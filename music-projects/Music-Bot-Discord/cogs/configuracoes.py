"""Cog de configurações por servidor."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.database import Database
from ui.embeds import embed_error, embed_success

logger = logging.getLogger(__name__)

# Cache em memória de configurações por servidor
_settings_cache: dict[int, dict] = {}  # type: ignore[type-arg]


class Configuracoes(commands.Cog, name="Configurações"):
    """Cog responsável pelas configurações do servidor."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _require_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False
        member = interaction.guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.followup.send(
                embed=embed_error("❌ Apenas administradores podem alterar as configurações."),
                ephemeral=True,
            )
            return False
        return True

    config_group = app_commands.Group(name="config", description="Configurações do servidor.")

    @config_group.command(name="dj-role", description="Define o cargo de DJ do servidor.")
    @app_commands.describe(cargo="Cargo que terá poderes de DJ")
    async def config_dj_role(self, interaction: discord.Interaction, cargo: discord.Role) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        await db.update_guild_settings(interaction.guild.id, dj_role_id=cargo.id)
        await interaction.followup.send(embed=embed_success(f"✅ Cargo de DJ definido para {cargo.mention}."), ephemeral=True)

    @config_group.command(name="volume-padrao", description="Define o volume padrão do servidor (0-150).")
    @app_commands.describe(nivel="Volume padrão (0-150)")
    async def config_volume(
        self, interaction: discord.Interaction, nivel: app_commands.Range[int, 0, 150]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        await db.update_guild_settings(interaction.guild.id, default_volume=nivel)
        await interaction.followup.send(embed=embed_success(f"✅ Volume padrão definido para **{nivel}%**."), ephemeral=True)

    @config_group.command(name="canal-texto", description="Define o canal de texto para mensagens do bot.")
    @app_commands.describe(canal="Canal de texto")
    async def config_canal_texto(
        self, interaction: discord.Interaction, canal: discord.TextChannel
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        await db.update_guild_settings(interaction.guild.id, text_channel_id=canal.id)
        await interaction.followup.send(embed=embed_success(f"✅ Canal de texto definido para {canal.mention}."), ephemeral=True)

    @config_group.command(name="max-fila", description="Define o número máximo de itens na fila.")
    @app_commands.describe(numero="Limite de itens (1-1000)")
    async def config_max_fila(
        self, interaction: discord.Interaction, numero: app_commands.Range[int, 1, 1000]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        await db.update_guild_settings(interaction.guild.id, max_queue_size=numero)
        from core.queue_manager import queue_registry
        queue_registry.update_max_size(interaction.guild.id, numero)
        await interaction.followup.send(embed=embed_success(f"✅ Limite da fila definido para **{numero}** itens."), ephemeral=True)

    @config_group.command(name="247", description="Ativa/desativa o modo 24/7.")
    @app_commands.describe(ativo="Ativar ou desativar")
    @app_commands.choices(ativo=[
        app_commands.Choice(name="Ativar", value="on"),
        app_commands.Choice(name="Desativar", value="off"),
    ])
    async def config_247(self, interaction: discord.Interaction, ativo: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        val = ativo == "on"
        await db.update_guild_settings(interaction.guild.id, mode_247=val)
        status = "ativado ✅" if val else "desativado ❌"
        await interaction.followup.send(embed=embed_success(f"Modo 24/7 {status}."), ephemeral=True)

    @config_group.command(name="idioma", description="Define o idioma do bot (reservado para futuras versões).")
    async def config_idioma(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            embed=embed_success("ℹ️ No momento, o bot funciona apenas em **Português do Brasil**. Suporte a outros idiomas em breve!"),
            ephemeral=True,
        )

    @config_group.command(name="palavras-bloqueadas", description="Define palavras-chave bloqueadas na busca (separadas por vírgula).")
    @app_commands.describe(palavras="Palavras separadas por vírgula (ex: spam,bot,teste)")
    async def config_blocked_keywords(self, interaction: discord.Interaction, palavras: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if not await self._require_admin(interaction):
            return
        if interaction.guild is None:
            return
        db = await Database.get()
        await db.ensure_guild(interaction.guild.id)
        await db.update_guild_settings(interaction.guild.id, blocked_keywords=palavras)
        await interaction.followup.send(embed=embed_success(f"✅ Palavras bloqueadas atualizadas."), ephemeral=True)

    @config_group.command(name="ver", description="Exibe as configurações atuais do servidor.")
    async def config_ver(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return
        db = await Database.get()
        gs = await db.get_guild_settings(interaction.guild.id)

        dj_role = interaction.guild.get_role(gs.dj_role_id) if gs.dj_role_id else None
        text_ch = interaction.guild.get_channel(gs.text_channel_id) if gs.text_channel_id else None

        em = discord.Embed(title="⚙️ Configurações do Servidor", color=discord.Color.blurple())
        em.add_field(name="Cargo DJ", value=dj_role.mention if dj_role else "Não definido", inline=True)
        em.add_field(name="Volume Padrão", value=f"{gs.default_volume}%", inline=True)
        em.add_field(name="Canal de Texto", value=text_ch.mention if text_ch else "Não definido", inline=True)
        em.add_field(name="Limite da Fila", value=str(gs.max_queue_size), inline=True)
        em.add_field(name="Modo 24/7", value="✅" if gs.mode_247 else "❌", inline=True)
        em.add_field(name="Inatividade", value=f"{gs.inactivity_timeout_minutes}min", inline=True)
        if gs.blocked_keywords:
            em.add_field(name="Palavras Bloqueadas", value=gs.blocked_keywords[:200], inline=False)
        await interaction.followup.send(embed=em, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Configuracoes(bot))
