"""Cog de gerenciamento da fila de músicas."""

from __future__ import annotations

import csv
import io
import json
import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.database import Database
from core.queue_manager import Track, queue_registry
from ui.embeds import embed_error, embed_queue, embed_success
from ui.views import QueueView
from utils.helpers import chunk_list

logger = logging.getLogger(__name__)


class Fila(commands.Cog, name="Fila"):
    """Cog responsável pelo gerenciamento da fila."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="queue", description="Exibe a fila de músicas.")
    async def queue(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        q = queue_registry.get(interaction.guild.id)
        tracks = q.queue
        current = q.current

        if not tracks and current is None:
            await interaction.followup.send(embed=embed_error("❌ A fila está vazia."), ephemeral=True)
            return

        view = QueueView(tracks, current, q.loop_mode)
        page_tracks = view.pages[0] if view.pages else []
        em = embed_queue(page_tracks, current, 1, max(len(view.pages), 1), q.loop_mode)
        await interaction.followup.send(embed=em, view=view)

    @app_commands.command(name="shuffle", description="Embaralha a fila de músicas.")
    async def shuffle(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        if q.is_empty:
            await interaction.followup.send(embed=embed_error("❌ A fila está vazia."), ephemeral=True)
            return
        await q.shuffle()
        await interaction.followup.send(embed=embed_success("🔀 Fila embaralhada!"))

    @app_commands.command(name="loop", description="Define o modo de repetição.")
    @app_commands.describe(modo="off = desativado, track = repetir faixa, queue = repetir fila")
    @app_commands.choices(modo=[
        app_commands.Choice(name="Desativado", value="off"),
        app_commands.Choice(name="Repetir Faixa", value="track"),
        app_commands.Choice(name="Repetir Fila", value="queue"),
    ])
    async def loop(self, interaction: discord.Interaction, modo: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        from core.queue_manager import LoopMode
        mode_map = {"off": LoopMode.OFF, "track": LoopMode.TRACK, "queue": LoopMode.QUEUE}
        q = queue_registry.get(interaction.guild.id)
        q.loop_mode = mode_map[modo]
        labels = {"off": "desativado ❌", "track": "🔂 repetir faixa", "queue": "🔁 repetir fila"}
        await interaction.followup.send(embed=embed_success(f"Loop: **{labels[modo]}**"))

    @app_commands.command(name="autoplay", description="Ativa/desativa autoplay ao esvaziar a fila.")
    async def autoplay(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        q.autoplay = not q.autoplay
        status = "ativado ✅" if q.autoplay else "desativado ❌"
        await interaction.followup.send(embed=embed_success(f"Autoplay {status}."))

    # Subcomandos de fila via grupo
    queue_group = app_commands.Group(name="queue", description="Gerenciamento da fila.")

    @queue_group.command(name="clear", description="Limpa toda a fila.")
    async def queue_clear(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        await q.clear()
        db = await Database.get()
        await db.clear_queue(interaction.guild.id)
        await interaction.followup.send(embed=embed_success("🗑️ Fila limpa!"))

    @queue_group.command(name="remove", description="Remove uma música da fila pela posição.")
    @app_commands.describe(posicao="Posição da música na fila (1 = primeira)")
    async def queue_remove(self, interaction: discord.Interaction, posicao: int) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        removed = await q.remove(posicao)
        if removed is None:
            await interaction.followup.send(embed=embed_error(f"❌ Posição inválida: {posicao}."), ephemeral=True)
            return
        await interaction.followup.send(embed=embed_success(f"🗑️ **{removed.title}** removida da fila."))

    @queue_group.command(name="move", description="Move uma música para outra posição na fila.")
    @app_commands.describe(de_posicao="Posição atual", para_posicao="Nova posição")
    async def queue_move(self, interaction: discord.Interaction, de_posicao: int, para_posicao: int) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        success = await q.move(de_posicao, para_posicao)
        if not success:
            await interaction.followup.send(embed=embed_error("❌ Posição inválida."), ephemeral=True)
            return
        await interaction.followup.send(embed=embed_success(f"↕️ Música movida da posição {de_posicao} para {para_posicao}."))

    @queue_group.command(name="export", description="Exporta a fila atual como arquivo JSON ou CSV.")
    @app_commands.describe(formato="Formato do arquivo exportado")
    @app_commands.choices(formato=[
        app_commands.Choice(name="JSON", value="json"),
        app_commands.Choice(name="CSV", value="csv"),
    ])
    async def queue_export(self, interaction: discord.Interaction, formato: str = "json") -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        tracks = q.queue
        if not tracks:
            await interaction.followup.send(embed=embed_error("❌ A fila está vazia."), ephemeral=True)
            return

        if formato == "json":
            data = json.dumps([t.to_dict() for t in tracks], ensure_ascii=False, indent=2)
            buf = io.BytesIO(data.encode("utf-8"))
            file = discord.File(buf, filename="fila.json")
        else:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["title", "url", "duration_seconds", "uploader", "requested_by"])
            for t in tracks:
                writer.writerow([t.title, t.url, t.duration_seconds, t.uploader, t.requested_by_name])
            file = discord.File(io.BytesIO(buf.getvalue().encode("utf-8")), filename="fila.csv")

        await interaction.followup.send(content=f"📤 Fila exportada com {len(tracks)} faixas.", file=file)

    @queue_group.command(name="import", description="Importa uma fila a partir de um arquivo JSON exportado.")
    @app_commands.describe(arquivo="Arquivo JSON exportado pelo /queue export")
    async def queue_import(self, interaction: discord.Interaction, arquivo: discord.Attachment) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        if not arquivo.filename.endswith(".json"):
            await interaction.followup.send(embed=embed_error("❌ Apenas arquivos .json são suportados."), ephemeral=True)
            return

        try:
            content = await arquivo.read()
            data = json.loads(content.decode("utf-8"))
            if not isinstance(data, list):
                raise ValueError("Formato inválido")
        except Exception:
            await interaction.followup.send(embed=embed_error("❌ Arquivo inválido ou corrompido."), ephemeral=True)
            return

        tracks = []
        for item in data:
            try:
                t = Track.from_dict(item)
                t.requested_by_id = interaction.user.id
                t.requested_by_name = str(interaction.user.display_name)
                tracks.append(t)
            except Exception:
                continue

        q = queue_registry.get(interaction.guild.id)
        added = await q.add_many(tracks)
        await interaction.followup.send(embed=embed_success(f"📥 {added} faixas importadas para a fila!"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fila(bot))
