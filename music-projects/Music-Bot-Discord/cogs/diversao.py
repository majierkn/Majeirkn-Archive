"""Cog de diversão: soundboard e quiz musical."""

from __future__ import annotations

import asyncio
import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from core.queue_manager import queue_registry
from ui.embeds import embed_error, embed_info, embed_success

logger = logging.getLogger(__name__)

# Sons curtos pré-cadastrados (nome → URL de áudio direto)
SOUNDBOARD: dict[str, str] = {
    "airhorn": "https://www.myinstants.com/media/sounds/air-horn.mp3",
    "applause": "https://www.myinstants.com/media/sounds/aplausos.mp3",
    "sad_trombone": "https://www.myinstants.com/media/sounds/sadtrombone.swf.mp3",
    "wow": "https://www.myinstants.com/media/sounds/wow.mp3",
    "bravo": "https://www.myinstants.com/media/sounds/bravo.mp3",
}

# Fragmentos de músicas para o quiz (título → URL de preview)
QUIZ_TRACKS = [
    {"title": "Bohemian Rhapsody", "artist": "Queen", "url": "https://www.youtube.com/watch?v=fJ9rUzIMcZQ"},
    {"title": "Stairway to Heaven", "artist": "Led Zeppelin", "url": "https://www.youtube.com/watch?v=QkF3oxziUI4"},
    {"title": "Hotel California", "artist": "Eagles", "url": "https://www.youtube.com/watch?v=BciS5krYL80"},
    {"title": "Smells Like Teen Spirit", "artist": "Nirvana", "url": "https://www.youtube.com/watch?v=hTWKbfoikeg"},
    {"title": "Sweet Child O' Mine", "artist": "Guns N' Roses", "url": "https://www.youtube.com/watch?v=1w7OgIMMRc4"},
]

# Rastreamento de reações nas mensagens de "Tocando Agora"
_reaction_data: dict[int, dict[str, int]] = {}  # guild_id → {thumbs_up, thumbs_down}


class Diversao(commands.Cog, name="Diversão"):
    """Cog responsável por funcionalidades de diversão e gamificação."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._quiz_active: dict[int, bool] = {}

    @app_commands.command(name="soundboard", description="Toca um efeito sonoro curto.")
    @app_commands.describe(som="Nome do efeito sonoro")
    @app_commands.choices(som=[
        app_commands.Choice(name=name, value=name) for name in SOUNDBOARD
    ])
    async def soundboard(self, interaction: discord.Interaction, som: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None or member.voice.channel is None:
            await interaction.followup.send(embed=embed_error("❌ Você precisa estar em um canal de voz!"), ephemeral=True)
            return

        if som not in SOUNDBOARD:
            await interaction.followup.send(embed=embed_error(f"❌ Som **{som}** não encontrado."), ephemeral=True)
            return

        url = SOUNDBOARD[som]
        vc = interaction.guild.voice_client

        if vc is None:
            vc = await member.voice.channel.connect()
        elif vc.is_playing():
            await interaction.followup.send(embed=embed_error("❌ Já está tocando algo. Aguarde terminar."), ephemeral=True)
            return

        source = discord.FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        vc.play(source)
        await interaction.followup.send(embed=embed_success(f"🔊 Tocando efeito: **{som}**"))

    quiz_group = app_commands.Group(name="quiz", description="Quiz musical interativo.")

    @quiz_group.command(name="musical", description="Inicia um quiz musical! Adivinhe o nome da música.")
    async def quiz_musical(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        if self._quiz_active.get(interaction.guild.id):
            await interaction.followup.send(embed=embed_error("❌ Já há um quiz ativo neste servidor."), ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None or member.voice.channel is None:
            await interaction.followup.send(embed=embed_error("❌ Você precisa estar em um canal de voz para o quiz!"), ephemeral=True)
            return

        track = random.choice(QUIZ_TRACKS)
        self._quiz_active[interaction.guild.id] = True

        vc = interaction.guild.voice_client
        if vc is None:
            vc = await member.voice.channel.connect()
        elif vc.is_playing():
            vc.stop()

        em = discord.Embed(
            title="🎵 Quiz Musical!",
            description="Ouça o trecho e tente adivinhar o nome da música ou artista no chat!\nVocê tem **30 segundos**.",
            color=discord.Color.gold(),
        )
        em.set_footer(text="Digite sua resposta no chat!")
        msg = await interaction.followup.send(embed=em)

        # Tocar preview (primeiros 30s via seek não disponível direto; tocamos do início)
        try:
            from core.player import resolve_audio_url
            audio_url = await resolve_audio_url(track["url"])
            source = discord.FFmpegPCMAudio(
                audio_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            )
            vc.play(source)
        except Exception as exc:
            logger.error("Erro ao tocar quiz: %s", exc)
            self._quiz_active[interaction.guild.id] = False
            await interaction.followup.send(embed=embed_error("❌ Não foi possível tocar o trecho. Tente novamente."), ephemeral=True)
            return

        # Aguardar resposta no chat
        channel = interaction.channel
        correct_answers = {track["title"].lower(), track["artist"].lower()}

        def check(m: discord.Message) -> bool:
            return (
                m.channel == channel
                and not m.author.bot
                and any(ans in m.content.lower() for ans in correct_answers)
            )

        try:
            answer_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            if vc.is_playing():
                vc.stop()
            winner_em = discord.Embed(
                title="🎉 Correto!",
                description=f"{answer_msg.author.mention} acertou!\n**{track['title']}** — {track['artist']}",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=winner_em)
        except asyncio.TimeoutError:
            if vc.is_playing():
                vc.stop()
            timeout_em = discord.Embed(
                title="⏰ Tempo Esgotado!",
                description=f"Ninguém acertou. A resposta era:\n**{track['title']}** — {track['artist']}",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=timeout_em)
        finally:
            self._quiz_active[interaction.guild.id] = False

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User | discord.Member) -> None:
        """Contabiliza reações 👍/👎 nas mensagens de Tocando Agora."""
        if user.bot:
            return
        if not hasattr(reaction.message, "guild") or reaction.message.guild is None:
            return

        guild_id = reaction.message.guild.id
        state_map = _reaction_data.setdefault(guild_id, {"thumbs_up": 0, "thumbs_down": 0})

        if str(reaction.emoji) == "👍":
            state_map["thumbs_up"] += 1
        elif str(reaction.emoji) == "👎":
            state_map["thumbs_down"] += 1

    @app_commands.command(name="reacoes", description="Exibe as reações da música atual.")
    async def reacoes(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        data = _reaction_data.get(interaction.guild.id, {"thumbs_up": 0, "thumbs_down": 0})
        em = discord.Embed(title="📊 Reações da Música Atual", color=discord.Color.blurple())
        em.add_field(name="👍 Curtidas", value=str(data["thumbs_up"]), inline=True)
        em.add_field(name="👎 Não curtidas", value=str(data["thumbs_down"]), inline=True)
        await interaction.followup.send(embed=em)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Diversao(bot))
