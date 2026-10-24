"""Cog de reprodução de música."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import get_settings
from core.database import Database
from core.player import (
    ExtractionError,
    PlayerState,
    extract_info,
    get_player_state,
    make_ffmpeg_source,
    make_volume_source,
    remove_player_state,
    resolve_audio_url,
    search_youtube,
)
from core.queue_manager import LoopMode, Track, queue_registry
from core.voting import VotingManager, required_votes_for
from ui.embeds import (
    embed_error,
    embed_history,
    embed_info,
    embed_lyrics,
    embed_now_playing,
    embed_success,
    embed_track_added,
    embed_warning,
)
from ui.views import NowPlayingView, SearchResultsView, VoteSkipView
from utils.helpers import is_url, member_voice_count, truncate
from utils.time_parser import format_duration, parse_time

logger = logging.getLogger(__name__)
settings = get_settings()

voting_manager = VotingManager()


class Musica(commands.Cog, name="Música"):
    """Cog responsável pela reprodução de músicas."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._progress_tasks: dict[int, asyncio.Task[None]] = {}
        self._inactivity_tasks: dict[int, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        """Garante que o bot está conectado ao canal do usuário."""
        if interaction.guild is None:
            return None
        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None or member.voice.channel is None:
            await interaction.followup.send(embed=embed_error("Você precisa estar em um canal de voz!"), ephemeral=True)
            return None

        vc = interaction.guild.voice_client
        channel = member.voice.channel

        if vc is None:
            try:
                vc = await channel.connect()  # type: ignore[assignment]
            except discord.ClientException as exc:
                await interaction.followup.send(embed=embed_error(f"Não consegui entrar no canal: {exc}"), ephemeral=True)
                return None
        elif vc.channel != channel:
            await vc.move_to(channel)

        return vc  # type: ignore[return-value]

    async def _check_dj(self, interaction: discord.Interaction) -> bool:
        """Retorna True se o usuário tem papel de DJ ou é admin."""
        if interaction.guild is None:
            return False
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            return False
        if member.guild_permissions.administrator:
            return True
        db = await Database.get()
        gs = await db.get_guild_settings(interaction.guild.id)
        if gs.dj_role_id:
            dj_role = interaction.guild.get_role(gs.dj_role_id)
            if dj_role and dj_role in member.roles:
                return True
        return False

    async def _check_blacklist(self, interaction: discord.Interaction) -> bool:
        """Retorna True se o usuário está na blacklist."""
        if interaction.guild is None:
            return False
        db = await Database.get()
        return await db.is_blacklisted(interaction.guild.id, interaction.user.id)

    def _cancel_inactivity(self, guild_id: int) -> None:
        task = self._inactivity_tasks.pop(guild_id, None)
        if task:
            task.cancel()

    def _schedule_inactivity(self, guild_id: int, timeout_minutes: int) -> None:
        self._cancel_inactivity(guild_id)

        async def _timeout() -> None:
            await asyncio.sleep(timeout_minutes * 60)
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return
            vc = guild.voice_client
            if vc and not vc.is_playing() and not vc.is_paused():
                await vc.disconnect()
                db = await Database.get()
                gs = await db.get_guild_settings(guild_id)
                if gs.text_channel_id:
                    ch = guild.get_channel(gs.text_channel_id)
                    if isinstance(ch, discord.TextChannel):
                        await ch.send(embed=embed_info("Desconectei por inatividade. Até logo! 👋"))

        self._inactivity_tasks[guild_id] = asyncio.create_task(_timeout())

    async def _play_next(self, guild_id: int) -> None:
        """Reproduz a próxima faixa da fila."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        vc = guild.voice_client
        q = queue_registry.get(guild_id)
        state = get_player_state(guild_id)

        track = await q.next()
        if track is None:
            # Fila vazia
            db = await Database.get()
            gs = await db.get_guild_settings(guild_id)
            if not gs.mode_247:
                self._schedule_inactivity(guild_id, gs.inactivity_timeout_minutes)
            # Salva fila vazia no banco
            await db.save_queue(guild_id, [])
            return

        # Resolve URL de streaming
        try:
            audio_url = await resolve_audio_url(track.webpage_url or track.url)
            track.audio_url = audio_url
        except ExtractionError as exc:
            db = await Database.get()
            gs = await db.get_guild_settings(guild_id)
            if gs.text_channel_id:
                ch = guild.get_channel(gs.text_channel_id)
                if isinstance(ch, discord.TextChannel):
                    await ch.send(embed=embed_error(str(exc)))
            asyncio.create_task(self._play_next(guild_id))
            return

        if vc is None or not vc.is_connected():
            return

        ffmpeg_opts = state.build_ffmpeg_options()
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
        volume_source = discord.PCMVolumeTransformer(source, volume=state.volume)
        state.on_play()

        def after_play(error: Exception | None) -> None:
            if error:
                logger.error("Erro na reprodução [guild %d]: %s", guild_id, error)
            asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.bot.loop)

        vc.play(volume_source, after=after_play)  # type: ignore[union-attr]

        # Salvar no histórico
        db = await Database.get()
        gs = await db.get_guild_settings(guild_id)
        await db.add_history(
            guild_id,
            track.requested_by_id,
            track.title,
            track.url,
            track.duration_seconds,
        )
        await db.save_queue(guild_id, q.to_dicts())

        # Enviar embed "Tocando Agora"
        if gs.text_channel_id:
            ch = guild.get_channel(gs.text_channel_id)
            if isinstance(ch, discord.TextChannel):
                np_embed = embed_now_playing(track, 0, int(state.volume * 100), q.loop_mode, track.requested_by_name)
                np_view = NowPlayingView()
                msg = await ch.send(embed=np_embed, view=np_view)
                state.nowplaying_message = msg
                self._start_progress_updater(guild_id, msg, track, state, q)

        # Presença do bot
        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name=truncate(track.title, 128))
        )

    def _start_progress_updater(
        self,
        guild_id: int,
        msg: discord.Message,
        track: Track,
        state: PlayerState,
        q: Any,
    ) -> None:
        """Atualiza a barra de progresso a cada 10s."""
        old_task = self._progress_tasks.pop(guild_id, None)
        if old_task:
            old_task.cancel()

        async def _update() -> None:
            while True:
                await asyncio.sleep(10)
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    break
                vc = guild.voice_client
                if vc is None or (not vc.is_playing() and not vc.is_paused()):
                    break
                try:
                    np_embed = embed_now_playing(
                        track, state.elapsed_seconds, int(state.volume * 100), q.loop_mode, track.requested_by_name
                    )
                    await msg.edit(embed=np_embed)
                except (discord.NotFound, discord.HTTPException):
                    break

        self._progress_tasks[guild_id] = asyncio.create_task(_update())

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(name="play", description="Toca uma música pelo nome ou link.")
    @app_commands.describe(busca="Nome da música ou URL (YouTube, Spotify, SoundCloud, etc.)")
    async def play(self, interaction: discord.Interaction, busca: str) -> None:
        await interaction.response.defer()

        if interaction.guild is None:
            return

        if await self._check_blacklist(interaction):
            await interaction.followup.send(embed=embed_error("Você está na blacklist deste servidor."), ephemeral=True)
            return

        db = await Database.get()
        gs = await db.get_guild_settings(interaction.guild.id)

        # Verificar palavras bloqueadas
        if gs.blocked_keywords:
            blocked = [kw.strip().lower() for kw in gs.blocked_keywords.split(",") if kw.strip()]
            if any(kw in busca.lower() for kw in blocked):
                await interaction.followup.send(embed=embed_error("❌ Essa busca contém palavras bloqueadas neste servidor."), ephemeral=True)
                return

        vc = await self._ensure_voice(interaction)
        if vc is None:
            return

        state = get_player_state(interaction.guild.id)
        q = queue_registry.get(interaction.guild.id, gs.max_queue_size)

        # Determinar se é URL ou busca
        is_playlist = False
        if is_url(busca):
            if "list=" in busca or "playlist" in busca or "album" in busca or "/sets/" in busca:
                is_playlist = True

        # Extração
        try:
            if not is_url(busca):
                # Busca no YouTube — mostrar seletor se múltiplos resultados
                results = await search_youtube(busca, max_results=5)
                if not results:
                    await interaction.followup.send(embed=embed_error("❌ Nenhum resultado encontrado."), ephemeral=True)
                    return

                if len(results) > 1:
                    from ui.embeds import embed_search_results
                    view = SearchResultsView(results)
                    em = embed_search_results(results)
                    msg = await interaction.followup.send(embed=em, view=view, ephemeral=True)
                    await view.wait()
                    if view.chosen is None:
                        await msg.edit(content="❌ Busca cancelada.", embed=None, view=None)
                        return
                    chosen = view.chosen
                else:
                    chosen = results[0]

                track = Track.from_ytdlp(
                    chosen,
                    requested_by_id=interaction.user.id,
                    requested_by_name=str(interaction.user.display_name),
                )
                track.webpage_url = chosen.get("url") or chosen.get("webpage_url") or ""
                added = await q.add(track)
                if not added:
                    await interaction.followup.send(embed=embed_error(f"❌ A fila está cheia ({gs.max_queue_size} itens)."), ephemeral=True)
                    return
                if not vc.is_playing() and not vc.is_paused():
                    await interaction.followup.send(embed=embed_info("▶️ Iniciando reprodução…"))
                    asyncio.create_task(self._play_next(interaction.guild.id))
                else:
                    await interaction.followup.send(embed=embed_track_added(track, q.size))
            elif is_playlist:
                data = await extract_info(busca, playlist=True)
                entries = data.get("entries", [])
                playlist_name = data.get("title", "Playlist")
                entries = [e for e in entries if e is not None]

                if len(entries) > 50:
                    await interaction.followup.send(embed=embed_info(f"📥 Importando **{playlist_name}** ({len(entries)} faixas)…"))

                tracks = [
                    Track.from_ytdlp(e, interaction.user.id, str(interaction.user.display_name))
                    for e in entries
                ]
                added_count = await q.add_many(tracks)

                from ui.embeds import embed_playlist_imported
                await interaction.followup.send(embed=embed_playlist_imported(playlist_name, added_count))
                if not vc.is_playing() and not vc.is_paused():
                    asyncio.create_task(self._play_next(interaction.guild.id))
            else:
                data = await extract_info(busca)
                track = Track.from_ytdlp(data, interaction.user.id, str(interaction.user.display_name))
                track.audio_url = data.get("url", "")
                added = await q.add(track)
                if not added:
                    await interaction.followup.send(embed=embed_error(f"❌ A fila está cheia ({gs.max_queue_size} itens)."), ephemeral=True)
                    return
                if not vc.is_playing() and not vc.is_paused():
                    await interaction.followup.send(embed=embed_info("▶️ Iniciando reprodução…"))
                    asyncio.create_task(self._play_next(interaction.guild.id))
                else:
                    await interaction.followup.send(embed=embed_track_added(track, q.size))

        except ExtractionError as exc:
            await interaction.followup.send(embed=embed_error(str(exc)), ephemeral=True)
        except Exception as exc:
            logger.exception("Erro no comando /play")
            await interaction.followup.send(embed=embed_error(f"❌ Erro inesperado: {exc}"), ephemeral=True)

    @app_commands.command(name="pause", description="Pausa a reprodução.")
    async def pause(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            get_player_state(interaction.guild.id).on_pause()
            await interaction.followup.send(embed=embed_success("⏸️ Pausado."))
        else:
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)

    @app_commands.command(name="resume", description="Retoma a reprodução.")
    async def resume(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            get_player_state(interaction.guild.id).on_resume()
            await interaction.followup.send(embed=embed_success("▶️ Retomado."))
        else:
            await interaction.followup.send(embed=embed_error("❌ A reprodução não está pausada."), ephemeral=True)

    @app_commands.command(name="stop", description="Para a reprodução, limpa a fila e desconecta.")
    async def stop(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        await q.clear()
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        db = await Database.get()
        await db.clear_queue(interaction.guild.id)
        remove_player_state(interaction.guild.id)
        await interaction.followup.send(embed=embed_success("⏹️ Reprodução encerrada e fila limpa."))
        await self.bot.change_presence(activity=None)

    @app_commands.command(name="skip", description="Pula para a próxima música.")
    async def skip(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        vc = interaction.guild.voice_client
        if vc is None or not (vc.is_playing() or vc.is_paused()):
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)
            return

        is_dj = await self._check_dj(interaction)
        if is_dj:
            vc.stop()
            await interaction.followup.send(embed=embed_success("⏭️ Música pulada pelo DJ."))
            return

        # Votação
        if not vc.channel:
            return
        member_count = member_voice_count(vc.channel)  # type: ignore[arg-type]
        required = required_votes_for(member_count - 1)  # excluir o próprio usuário

        session = voting_manager.start_vote(interaction.guild.id, "skip", required, interaction.user.id)

        if session.passed:
            vc.stop()
            await interaction.followup.send(embed=embed_success("⏭️ Música pulada por votação!"))
            voting_manager.end_vote(interaction.guild.id)
            return

        view = VoteSkipView(session)
        msg = await interaction.followup.send(
            embed=embed_info(f"🗳️ Votação para pular iniciada!\n{interaction.user.mention} iniciou. ({session.progress} votos necessários.)"),
            view=view,
        )
        await view.wait()
        if session.passed:
            vc.stop()
            await msg.edit(embed=embed_success("⏭️ Votos suficientes! Pulando…"), view=None)
        else:
            await msg.edit(embed=embed_error("❌ Votos insuficientes. Música não pulada."), view=None)
        voting_manager.end_vote(interaction.guild.id)

    @app_commands.command(name="seek", description="Avança para um tempo específico na música.")
    @app_commands.describe(tempo="Tempo no formato mm:ss ou segundos (ex: 1:30 ou 90)")
    async def seek(self, interaction: discord.Interaction, tempo: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        vc = interaction.guild.voice_client
        if vc is None or not (vc.is_playing() or vc.is_paused()):
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)
            return

        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None or current.is_stream:
            await interaction.followup.send(embed=embed_error("❌ Não é possível usar /seek em streams ao vivo."), ephemeral=True)
            return

        seconds = parse_time(tempo)
        if seconds is None:
            await interaction.followup.send(embed=embed_error("❌ Formato de tempo inválido. Use mm:ss ou segundos (ex: 1:30 ou 90)."), ephemeral=True)
            return

        if seconds > current.duration_seconds:
            await interaction.followup.send(embed=embed_error("❌ O tempo informado é maior que a duração da música."), ephemeral=True)
            return

        state = get_player_state(interaction.guild.id)
        audio_url = current.audio_url or current.url

        vc.stop()
        ffmpeg_opts = state.build_ffmpeg_options(seek_seconds=seconds)
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
        volume_source = discord.PCMVolumeTransformer(source, volume=state.volume)
        state.on_play(position_offset=seconds)

        def after_play(error: Exception | None) -> None:
            if error:
                logger.error("Erro após seek [guild %d]: %s", interaction.guild.id, error)  # type: ignore[union-attr]
            asyncio.run_coroutine_threadsafe(self._play_next(interaction.guild.id), self.bot.loop)  # type: ignore[union-attr]

        vc.play(volume_source, after=after_play)
        await interaction.followup.send(embed=embed_success(f"⏩ Avançado para **{format_duration(seconds)}**."))

    @app_commands.command(name="replay", description="Reinicia a música atual do início.")
    async def replay(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None:
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)
            return
        # Coloca a faixa atual de volta na frente da fila e pula
        q._queue.insert(0, current)
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
        await interaction.followup.send(embed=embed_success("🔄 Reiniciando a música atual…"))

    @app_commands.command(name="previous", description="Volta para a música anterior.")
    async def previous(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        prev = await q.previous()
        if prev is None:
            await interaction.followup.send(embed=embed_error("❌ Não há faixa anterior no histórico."), ephemeral=True)
            return
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
        await interaction.followup.send(embed=embed_success(f"⏮️ Voltando para **{prev.title}**…"))

    @app_commands.command(name="volume", description="Ajusta o volume da reprodução (0-150%).")
    @app_commands.describe(nivel="Volume de 0 a 150")
    async def volume(self, interaction: discord.Interaction, nivel: app_commands.Range[int, 0, 150]) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        state = get_player_state(interaction.guild.id)
        state.volume = nivel / 100.0

        vc = interaction.guild.voice_client
        if vc and vc.source and hasattr(vc.source, "volume"):
            vc.source.volume = state.volume  # type: ignore[union-attr]

        db = await Database.get()
        await db.update_guild_settings(interaction.guild.id, default_volume=nivel)
        await interaction.followup.send(embed=embed_success(f"🔊 Volume ajustado para **{nivel}%**."))

    @app_commands.command(name="nowplaying", description="Mostra informações sobre a música atual.")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None:
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)
            return

        state = get_player_state(interaction.guild.id)
        view = NowPlayingView()
        em = embed_now_playing(current, state.elapsed_seconds, int(state.volume * 100), q.loop_mode, current.requested_by_name)
        await interaction.followup.send(embed=em, view=view)

    @app_commands.command(name="join", description="Entra no seu canal de voz.")
    async def join(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        vc = await self._ensure_voice(interaction)
        if vc:
            await interaction.followup.send(embed=embed_success(f"✅ Conectado em **{vc.channel}**."))

    @app_commands.command(name="leave", description="Sai do canal de voz.")
    async def leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        vc = interaction.guild.voice_client
        if vc:
            q = queue_registry.get(interaction.guild.id)
            await q.clear()
            vc.stop()
            await vc.disconnect()
            remove_player_state(interaction.guild.id)
            await interaction.followup.send(embed=embed_success("👋 Desconectado."))
        else:
            await interaction.followup.send(embed=embed_error("❌ Não estou em nenhum canal de voz."), ephemeral=True)

    @app_commands.command(name="247", description="Alterna o modo 24/7 (bot permanece no canal mesmo sem música).")
    async def mode_247(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        if not await self._check_dj(interaction):
            await interaction.followup.send(embed=embed_error("❌ Apenas DJs podem usar este comando."), ephemeral=True)
            return
        db = await Database.get()
        gs = await db.get_guild_settings(interaction.guild.id)
        new_val = not gs.mode_247
        await db.update_guild_settings(interaction.guild.id, mode_247=new_val)
        status = "ativado ✅" if new_val else "desativado ❌"
        await interaction.followup.send(embed=embed_success(f"Modo 24/7 {status}."))

    @app_commands.command(name="sleeptimer", description="Para a reprodução após X minutos.")
    @app_commands.describe(minutos="Minutos até parar a reprodução")
    async def sleeptimer(self, interaction: discord.Interaction, minutos: app_commands.Range[int, 1, 480]) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        state = get_player_state(interaction.guild.id)
        if state.sleep_timer_task:
            state.sleep_timer_task.cancel()

        guild_id = interaction.guild.id

        async def _sleep() -> None:
            await asyncio.sleep(minutos * 60)
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                return
            vc = guild.voice_client
            if vc:
                q = queue_registry.get(guild_id)
                await q.clear()
                vc.stop()
                await vc.disconnect()
                db = await Database.get()
                gs = await db.get_guild_settings(guild_id)
                if gs.text_channel_id:
                    ch = guild.get_channel(gs.text_channel_id)
                    if isinstance(ch, discord.TextChannel):
                        await ch.send(embed=embed_info("💤 Sleep timer ativado. Boa noite!"))

        state.sleep_timer_task = asyncio.create_task(_sleep())
        await interaction.followup.send(embed=embed_success(f"💤 Sleep timer definido para **{minutos} minuto(s)**."))

    @app_commands.command(name="lyrics", description="Exibe a letra da música atual.")
    async def lyrics(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None:
            await interaction.followup.send(embed=embed_error("❌ Nada está tocando."), ephemeral=True)
            return

        title = current.title
        artist = current.uploader

        # Tentar limpar o título (remover "(Official Video)", etc.)
        import re
        clean_title = re.sub(r"\(.*?\)|\[.*?\]|feat\..+|ft\..+", "", title, flags=re.IGNORECASE).strip()

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.lyrics_api_url}/{artist}/{clean_title}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lyrics_text = data.get("lyrics", "")
                        if lyrics_text:
                            await interaction.followup.send(embed=embed_lyrics(title, lyrics_text))
                            return
        except Exception:
            pass

        # Fallback: busca só pelo título
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.lyrics_api_url}/a/{clean_title}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lyrics_text = data.get("lyrics", "")
                        if lyrics_text:
                            await interaction.followup.send(embed=embed_lyrics(title, lyrics_text))
                            return
        except Exception:
            pass

        await interaction.followup.send(embed=embed_error("❌ Letra não encontrada para esta música."), ephemeral=True)

    @app_commands.command(name="history", description="Mostra as últimas músicas tocadas.")
    async def history(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        db = await Database.get()
        entries = await db.get_history(interaction.guild.id, limit=20)
        await interaction.followup.send(embed=embed_history(entries))

    @app_commands.command(name="meusdados", description="Gerencia seus dados pessoais.")
    @app_commands.describe(acao="excluir: apaga todos os seus dados do bot")
    @app_commands.choices(acao=[app_commands.Choice(name="excluir", value="excluir")])
    async def meusdados(self, interaction: discord.Interaction, acao: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if acao == "excluir":
            db = await Database.get()
            await db.delete_user_data(interaction.user.id)
            await interaction.followup.send(
                embed=embed_success("✅ Todos os seus dados (playlists e histórico) foram removidos."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Musica(bot))
