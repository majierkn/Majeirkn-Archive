"""Cog de administração do bot (restrito ao dono)."""

from __future__ import annotations

import io
import logging
import os
import time

import discord
from discord import app_commands
from discord.ext import commands

from ui.embeds import embed_error, embed_success

logger = logging.getLogger(__name__)

START_TIME = time.monotonic()


class Admin(commands.Cog, name="Admin"):
    """Cog de administração — restrito ao dono do bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _is_owner(self, interaction: discord.Interaction) -> bool:
        app = await self.bot.application_info()
        if app.team:
            return interaction.user.id in {m.id for m in app.team.members}
        return interaction.user.id == app.owner.id

    async def _owner_check(self, interaction: discord.Interaction) -> bool:
        if not await self._is_owner(interaction):
            await interaction.followup.send(
                embed=embed_error("❌ Este comando é restrito ao dono do bot."),
                ephemeral=True,
            )
            return False
        return True

    @app_commands.command(name="sync", description="[Admin] Sincroniza slash commands.")
    @app_commands.describe(servidor="Sincronizar apenas neste servidor (mais rápido)")
    async def sync(self, interaction: discord.Interaction, servidor: bool = False) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._owner_check(interaction):
            return

        if servidor and interaction.guild:
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(
                embed=embed_success(f"✅ {len(synced)} comando(s) sincronizados neste servidor."),
                ephemeral=True,
            )
        else:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                embed=embed_success(f"✅ {len(synced)} comando(s) sincronizados globalmente."),
                ephemeral=True,
            )

    @app_commands.command(name="ping", description="Mostra a latência do gateway.")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        latency = round(self.bot.latency * 1000)
        await interaction.followup.send(embed=embed_success(f"🏓 Pong! Latência: **{latency}ms**"))

    @app_commands.command(name="status", description="[Admin] Mostra status do bot.")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._owner_check(interaction):
            return

        uptime_s = int(time.monotonic() - START_TIME)
        h, rem = divmod(uptime_s, 3600)
        m, s = divmod(rem, 60)

        em = discord.Embed(title="📊 Status do Bot", color=discord.Color.green())
        em.add_field(name="Uptime", value=f"{h}h {m}min {s}s", inline=True)
        em.add_field(name="Servidores", value=str(len(self.bot.guilds)), inline=True)
        em.add_field(name="Latência", value=f"{round(self.bot.latency * 1000)}ms", inline=True)

        try:
            import psutil
            proc = psutil.Process()
            mem_mb = proc.memory_info().rss / 1024 / 1024
            cpu = psutil.cpu_percent(interval=0.1)
            em.add_field(name="Memória RAM", value=f"{mem_mb:.1f} MB", inline=True)
            em.add_field(name="CPU", value=f"{cpu:.1f}%", inline=True)
        except ImportError:
            em.add_field(name="Memória/CPU", value="psutil não disponível", inline=True)

        voice_count = sum(1 for g in self.bot.guilds if g.voice_client and g.voice_client.is_connected())
        em.add_field(name="Canais de Voz Ativos", value=str(voice_count), inline=True)

        await interaction.followup.send(embed=em, ephemeral=True)

    @app_commands.command(name="restart", description="[Admin] Reinicia o bot graciosamente.")
    async def restart(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._owner_check(interaction):
            return

        from core.database import Database
        from core.queue_manager import queue_registry

        # Salvar todas as filas ativas antes de reiniciar
        db = await Database.get()
        for guild in self.bot.guilds:
            if guild.voice_client and guild.voice_client.is_connected():
                q = queue_registry.get(guild.id)
                tracks = q.to_dicts()
                await db.save_queue(guild.id, tracks)

        await interaction.followup.send(embed=embed_success("♻️ Reiniciando…"), ephemeral=True)
        logger.info("Reinício solicitado via /restart pelo usuário %s", interaction.user)
        await self.bot.close()

    @app_commands.command(name="backup", description="[Admin] Envia um backup do banco de dados.")
    async def backup(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._owner_check(interaction):
            return

        db_path = os.environ.get("DB_PATH", "data/bot.db")
        if not os.path.exists(db_path):
            await interaction.followup.send(embed=embed_error("❌ Arquivo do banco não encontrado."), ephemeral=True)
            return

        with open(db_path, "rb") as f:
            data = f.read()

        file = discord.File(io.BytesIO(data), filename="bot_backup.db")
        await interaction.followup.send(content="📦 Backup do banco de dados:", file=file, ephemeral=True)

    blacklist_group = app_commands.Group(name="blacklist", description="Gerenciamento da blacklist.")

    @blacklist_group.command(name="add", description="Adiciona um usuário à blacklist.")
    @app_commands.describe(usuario="Usuário a bloquear", motivo="Motivo do bloqueio")
    async def blacklist_add(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        motivo: str = "",
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return
        member = interaction.guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.followup.send(embed=embed_error("❌ Apenas administradores podem gerenciar a blacklist."), ephemeral=True)
            return

        from core.database import Database
        db = await Database.get()
        await db.add_blacklist(interaction.guild.id, usuario.id, motivo)
        await interaction.followup.send(
            embed=embed_success(f"✅ {usuario.mention} adicionado(a) à blacklist."),
            ephemeral=True,
        )

    @blacklist_group.command(name="remove", description="Remove um usuário da blacklist.")
    @app_commands.describe(usuario="Usuário a remover")
    async def blacklist_remove(self, interaction: discord.Interaction, usuario: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return
        member = interaction.guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.followup.send(embed=embed_error("❌ Apenas administradores podem gerenciar a blacklist."), ephemeral=True)
            return

        from core.database import Database
        db = await Database.get()
        removed = await db.remove_blacklist(interaction.guild.id, usuario.id)
        if removed:
            await interaction.followup.send(embed=embed_success(f"✅ {usuario.mention} removido(a) da blacklist."), ephemeral=True)
        else:
            await interaction.followup.send(embed=embed_error(f"❌ {usuario.mention} não está na blacklist."), ephemeral=True)

    @blacklist_group.command(name="list", description="Lista usuários na blacklist.")
    async def blacklist_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return

        from core.database import Database
        db = await Database.get()
        entries = await db.get_blacklist(interaction.guild.id)
        if not entries:
            await interaction.followup.send(embed=embed_success("A blacklist está vazia."), ephemeral=True)
            return

        lines = []
        for e in entries:
            user = self.bot.get_user(e["user_id"])
            name = str(user) if user else str(e["user_id"])
            motivo = e.get("reason") or "Sem motivo"
            lines.append(f"• {name} — {motivo}")

        em = discord.Embed(title="🚫 Blacklist", description="\n".join(lines[:30]), color=discord.Color.red())
        await interaction.followup.send(embed=em, ephemeral=True)

    @app_commands.command(name="stats", description="Mostra estatísticas de músicas do servidor.")
    async def stats(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        from core.database import Database
        from ui.embeds import embed_stats
        db = await Database.get()
        totals = await db.get_guild_totals(interaction.guild.id)
        top = await db.get_top_tracks(interaction.guild.id, 10)
        em = embed_stats(interaction.guild.name, totals["total_tracks"], totals["total_seconds"], top)
        await interaction.followup.send(embed=em)

    @app_commands.command(name="topmusicas", description="Mostra o ranking das músicas mais tocadas.")
    async def topmusicas(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        from core.database import Database
        from ui.embeds import embed_stats
        db = await Database.get()
        totals = await db.get_guild_totals(interaction.guild.id)
        top = await db.get_top_tracks(interaction.guild.id, 10)
        em = embed_stats(interaction.guild.name, totals["total_tracks"], totals["total_seconds"], top)
        em.title = "🏆 Top Músicas"
        await interaction.followup.send(embed=em)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
