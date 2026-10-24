from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

from utils.embeds import erro_embed, info_embed, sucesso_embed

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    url: str
    webpage_url: str
    requester_id: int


class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queues: dict[int, deque[Track]] = {}
        self.volumes: dict[int, float] = {}

    async def extract_track(self, query: str, requester_id: int) -> Track:
        def run():
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
                data = ytdl.extract_info(query, download=False)
                if "entries" in data:
                    data = data["entries"][0]
                return data
        data = await asyncio.to_thread(run)
        return Track(
            title=data.get("title", "Sem título"),
            url=data["url"],
            webpage_url=data.get("webpage_url", query),
            requester_id=requester_id,
        )

    def queue(self, guild_id: int) -> deque[Track]:
        return self.queues.setdefault(guild_id, deque())

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(embed=erro_embed("Canal de voz", "Entre em um canal de voz primeiro."), ephemeral=True)
            return None
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc is None:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)
        return vc

    def play_next(self, guild: discord.Guild) -> None:
        vc = guild.voice_client
        if vc is None or not self.queue(guild.id):
            return
        track = self.queue(guild.id).popleft()
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTIONS), volume=self.volumes.get(guild.id, 0.5))
        vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, guild))

    @app_commands.command(name="entrar_voz", description="Fazer o bot entrar no seu canal de voz.")
    @app_commands.guild_only()
    async def entrar_voz(self, interaction: discord.Interaction) -> None:
        vc = await self.ensure_voice(interaction)
        if vc:
            await interaction.response.send_message(embed=sucesso_embed("Conectado", f"Entrei em `{vc.channel}`."))

    @app_commands.command(name="sair_voz", description="Fazer o bot sair do canal de voz.")
    @app_commands.guild_only()
    async def sair_voz(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message(embed=erro_embed("Não conectado", "Não estou em um canal de voz."), ephemeral=True)
            return
        await vc.disconnect(force=True)
        self.queue(interaction.guild_id).clear()
        await interaction.response.send_message(embed=sucesso_embed("Desconectado", "Saí do canal de voz e limpei a fila."))

    @app_commands.command(name="tocar", description="Tocar música do YouTube por nome ou URL.")
    @app_commands.guild_only()
    async def tocar(self, interaction: discord.Interaction, busca: str) -> None:
        await interaction.response.defer()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            await interaction.followup.send(embed=erro_embed("Canal de voz", "Entre em um canal de voz primeiro."), ephemeral=True)
            return
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        try:
            track = await self.extract_track(busca, interaction.user.id)
        except Exception as exc:
            await interaction.followup.send(embed=erro_embed("Erro no yt-dlp", f"Não consegui carregar a música: `{exc}`"), ephemeral=True)
            return
        if vc.is_playing() or vc.is_paused():
            self.queue(interaction.guild_id).append(track)
            await interaction.followup.send(embed=sucesso_embed("Adicionado à fila", f"**{track.title}**\n{track.webpage_url}"))
        else:
            self.queue(interaction.guild_id).appendleft(track)
            self.play_next(interaction.guild)
            await interaction.followup.send(embed=sucesso_embed("Tocando agora", f"**{track.title}**\n{track.webpage_url}"))

    @app_commands.command(name="pausar_musica", description="Pausar a música atual.")
    @app_commands.guild_only()
    async def pausar_musica(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message(embed=erro_embed("Nada tocando", "Não há música tocando."), ephemeral=True)
            return
        vc.pause()
        await interaction.response.send_message(embed=sucesso_embed("Pausado", "Música pausada."))

    @app_commands.command(name="continuar_musica", description="Continuar música pausada.")
    @app_commands.guild_only()
    async def continuar_musica(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            await interaction.response.send_message(embed=erro_embed("Nada pausado", "Não há música pausada."), ephemeral=True)
            return
        vc.resume()
        await interaction.response.send_message(embed=sucesso_embed("Continuando", "Música retomada."))

    @app_commands.command(name="parar_musica", description="Parar música e limpar fila.")
    @app_commands.guild_only()
    async def parar_musica(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        self.queue(interaction.guild_id).clear()
        if vc:
            vc.stop()
        await interaction.response.send_message(embed=sucesso_embed("Parado", "Música parada e fila limpa."))

    @app_commands.command(name="pular_musica", description="Pular música atual.")
    @app_commands.guild_only()
    async def pular_musica(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message(embed=erro_embed("Nada tocando", "Não há música para pular."), ephemeral=True)
            return
        vc.stop()
        await interaction.response.send_message(embed=sucesso_embed("Pulada", "Música pulada."))

    @app_commands.command(name="fila_musica", description="Ver fila de músicas.")
    @app_commands.guild_only()
    async def fila_musica(self, interaction: discord.Interaction) -> None:
        q = list(self.queue(interaction.guild_id))
        if not q:
            await interaction.response.send_message(embed=info_embed("Fila", "A fila está vazia."))
            return
        lines = [f"`{i}.` **{t.title}**" for i, t in enumerate(q[:10], 1)]
        await interaction.response.send_message(embed=info_embed("Fila de músicas", "\n".join(lines)))

    @app_commands.command(name="volume_musica", description="Definir volume da música.")
    @app_commands.guild_only()
    async def volume_musica(self, interaction: discord.Interaction, volume: app_commands.Range[int, 1, 100]) -> None:
        self.volumes[interaction.guild_id] = volume / 100
        vc = interaction.guild.voice_client
        if vc and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = volume / 100
        await interaction.response.send_message(embed=sucesso_embed("Volume atualizado", f"Volume definido para `{volume}%`."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Musica(bot))
