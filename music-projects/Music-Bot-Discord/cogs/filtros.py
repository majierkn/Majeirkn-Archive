"""Cog de filtros de áudio."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.player import AUDIO_FILTERS, get_player_state
from core.queue_manager import queue_registry
from ui.embeds import embed_error, embed_success

logger = logging.getLogger(__name__)


class Filtros(commands.Cog, name="Filtros"):
    """Cog responsável pelos filtros de áudio via FFmpeg."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _apply_filters(self, interaction: discord.Interaction) -> bool:
        """Reaplicar filtros parando e reiniciando a fonte de áudio."""
        if interaction.guild is None:
            return False

        vc = interaction.guild.voice_client
        if vc is None or not (vc.is_playing() or vc.is_paused()):
            return False

        state = get_player_state(interaction.guild.id)
        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None:
            return False

        from core.player import ExtractionError, resolve_audio_url
        try:
            audio_url = current.audio_url or await resolve_audio_url(current.webpage_url or current.url)
            current.audio_url = audio_url
        except ExtractionError:
            return False

        import asyncio
        seek_pos = state.elapsed_seconds
        ffmpeg_opts = state.build_ffmpeg_options(seek_seconds=seek_pos)
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
        volume_source = discord.PCMVolumeTransformer(source, volume=state.volume)

        vc.stop()
        state.on_play(position_offset=seek_pos)

        def after_play(error: Exception | None) -> None:
            if error:
                logger.error("Erro após aplicar filtro [guild %d]: %s", interaction.guild.id, error)  # type: ignore[union-attr]
            asyncio.run_coroutine_threadsafe(
                self.bot.cogs["Música"]._play_next(interaction.guild.id),  # type: ignore[index]
                self.bot.loop,
            )

        vc.play(volume_source, after=after_play)
        return True

    # ---- /filter ----

    filter_group = app_commands.Group(name="filter", description="Filtros de áudio.")

    @filter_group.command(name="bassboost", description="Ativa/desativa o filtro Bass Boost.")
    async def filter_bassboost(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["bassboost"] = not state.active_filters.get("bassboost", False)
        status = "ativado ✅" if state.active_filters["bassboost"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🎸 Bass Boost {status}."))

    @filter_group.command(name="nightcore", description="Ativa/desativa o filtro Nightcore.")
    async def filter_nightcore(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["nightcore"] = not state.active_filters.get("nightcore", False)
        # Nightcore e vaporwave são mutuamente exclusivos
        if state.active_filters["nightcore"]:
            state.active_filters["vaporwave"] = False
        status = "ativado ✅" if state.active_filters["nightcore"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🌙 Nightcore {status}."))

    @filter_group.command(name="vaporwave", description="Ativa/desativa o filtro Vaporwave.")
    async def filter_vaporwave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["vaporwave"] = not state.active_filters.get("vaporwave", False)
        if state.active_filters["vaporwave"]:
            state.active_filters["nightcore"] = False
        status = "ativado ✅" if state.active_filters["vaporwave"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🌊 Vaporwave {status}."))

    @filter_group.command(name="8d", description="Ativa/desativa o filtro 8D Audio.")
    async def filter_8d(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["8d"] = not state.active_filters.get("8d", False)
        status = "ativado ✅" if state.active_filters["8d"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🎧 8D Audio {status}."))

    @filter_group.command(name="karaoke", description="Ativa/desativa o filtro Karaokê (remove vocal).")
    async def filter_karaoke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["karaoke"] = not state.active_filters.get("karaoke", False)
        status = "ativado ✅" if state.active_filters["karaoke"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🎤 Karaokê {status}."))

    @filter_group.command(name="tremolo", description="Ativa/desativa o filtro Tremolo.")
    async def filter_tremolo(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["tremolo"] = not state.active_filters.get("tremolo", False)
        status = "ativado ✅" if state.active_filters["tremolo"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"〰️ Tremolo {status}."))

    @filter_group.command(name="vibrato", description="Ativa/desativa o filtro Vibrato.")
    async def filter_vibrato(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters["vibrato"] = not state.active_filters.get("vibrato", False)
        status = "ativado ✅" if state.active_filters["vibrato"] else "desativado ❌"
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success(f"🎵 Vibrato {status}."))

    @filter_group.command(name="reset", description="Remove todos os filtros ativos.")
    async def filter_reset(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        state = get_player_state(interaction.guild.id)
        state.active_filters.clear()
        state.equalizer_bands.clear()
        await self._apply_filters(interaction)
        await interaction.followup.send(embed=embed_success("🔄 Todos os filtros foram removidos."))

    @app_commands.command(name="equalizer", description="Ajusta uma banda do equalizador.")
    @app_commands.describe(
        frequencia="Frequência em Hz (ex: 60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000)",
        ganho="Ganho em dB (-12 a +12)",
    )
    async def equalizer(
        self,
        interaction: discord.Interaction,
        frequencia: int,
        ganho: app_commands.Range[float, -12.0, 12.0],
    ) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        valid_freqs = {60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000}
        if frequencia not in valid_freqs:
            await interaction.followup.send(
                embed=embed_error(f"❌ Frequência inválida. Use uma destas: {', '.join(map(str, sorted(valid_freqs)))} Hz"),
                ephemeral=True,
            )
            return

        state = get_player_state(interaction.guild.id)
        if ganho == 0:
            state.equalizer_bands.pop(str(frequencia), None)
        else:
            state.equalizer_bands[str(frequencia)] = ganho

        await self._apply_filters(interaction)
        action = "removida" if ganho == 0 else f"ajustada para **{ganho:+.1f} dB**"
        await interaction.followup.send(
            embed=embed_success(f"🎛️ Banda **{frequencia} Hz** {action}.")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Filtros(bot))
