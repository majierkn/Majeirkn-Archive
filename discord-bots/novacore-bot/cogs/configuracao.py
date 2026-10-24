from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_permissions
from utils.embeds import info_embed, sucesso_embed


class Configuracao(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _admin(self, interaction: discord.Interaction) -> bool:
        return await require_permissions(interaction, manage_guild=True)

    @app_commands.command(name="config_logs", description="Configurar canal de logs.")
    @app_commands.guild_only()
    async def config_logs(self, interaction: discord.Interaction, canal: discord.TextChannel) -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "logs.canal_id", canal.id)
        await interaction.response.send_message(embed=sucesso_embed("Logs configurados", f"Canal de logs definido para {canal.mention}."), ephemeral=True)

    @app_commands.command(name="config_boasvindas", description="Configurar canal e mensagem de boas-vindas.")
    @app_commands.guild_only()
    async def config_boasvindas(self, interaction: discord.Interaction, canal: discord.TextChannel, mensagem: str = "Bem-vindo(a), {user}, ao {server}!") -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "welcome.canal_id", canal.id)
        await self.bot.db.set_setting(interaction.guild_id, "welcome.mensagem", mensagem)
        await interaction.response.send_message(embed=sucesso_embed("Boas-vindas configuradas", f"Canal: {canal.mention}\nMensagem: `{mensagem}`"), ephemeral=True)

    @app_commands.command(name="config_saida", description="Configurar canal e mensagem de saída.")
    @app_commands.guild_only()
    async def config_saida(self, interaction: discord.Interaction, canal: discord.TextChannel, mensagem: str = "{user} saiu do servidor.") -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "leave.canal_id", canal.id)
        await self.bot.db.set_setting(interaction.guild_id, "leave.mensagem", mensagem)
        await interaction.response.send_message(embed=sucesso_embed("Saída configurada", f"Canal: {canal.mention}\nMensagem: `{mensagem}`"), ephemeral=True)

    @app_commands.command(name="config_autocargo", description="Configurar cargo automático para novos membros.")
    @app_commands.guild_only()
    async def config_autocargo(self, interaction: discord.Interaction, cargo: discord.Role) -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "autorole.role_id", cargo.id)
        await interaction.response.send_message(embed=sucesso_embed("Auto cargo configurado", f"Cargo automático: {cargo.mention}."), ephemeral=True)

    @app_commands.command(name="config_ticket", description="Configurar categoria e cargo da equipe de tickets.")
    @app_commands.guild_only()
    async def config_ticket(self, interaction: discord.Interaction, categoria: discord.CategoryChannel, cargo_equipe: discord.Role) -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "tickets.category_id", categoria.id)
        await self.bot.db.set_setting(interaction.guild_id, "tickets.support_role_id", cargo_equipe.id)
        await interaction.response.send_message(embed=sucesso_embed("Tickets configurados", f"Categoria: `{categoria.name}`\nEquipe: {cargo_equipe.mention}"), ephemeral=True)

    @app_commands.command(name="config_automod", description="Configurar AutoMod do servidor.")
    @app_commands.guild_only()
    async def config_automod(self, interaction: discord.Interaction, ativado: bool, bloquear_links: bool = True, palavras_proibidas: str = "", caps_percent: app_commands.Range[int, 50, 100] = 75) -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "automod.enabled", ativado)
        await self.bot.db.set_setting(interaction.guild_id, "automod.block_links", bloquear_links)
        await self.bot.db.set_setting(interaction.guild_id, "automod.bad_words", [p.strip().lower() for p in palavras_proibidas.split(",") if p.strip()])
        await self.bot.db.set_setting(interaction.guild_id, "automod.caps_percent", caps_percent)
        await interaction.response.send_message(embed=sucesso_embed("AutoMod configurado", f"Ativado: `{ativado}`\nLinks: `{bloquear_links}`\nCaps: `{caps_percent}%`"), ephemeral=True)

    @app_commands.command(name="config_xp", description="Configurar sistema de XP.")
    @app_commands.guild_only()
    async def config_xp(self, interaction: discord.Interaction, ativado: bool = True, cooldown: app_commands.Range[int, 5, 600] = 60, xp_min: app_commands.Range[int, 1, 100] = 15, xp_max: app_commands.Range[int, 1, 200] = 30) -> None:
        if not await self._admin(interaction): return
        if xp_max < xp_min:
            xp_max = xp_min
        await self.bot.db.set_setting(interaction.guild_id, "xp.enabled", ativado)
        await self.bot.db.set_setting(interaction.guild_id, "xp.cooldown", cooldown)
        await self.bot.db.set_setting(interaction.guild_id, "xp.min", xp_min)
        await self.bot.db.set_setting(interaction.guild_id, "xp.max", xp_max)
        await interaction.response.send_message(embed=sucesso_embed("XP configurado", f"Ativado: `{ativado}`\nCooldown: `{cooldown}s`\nGanho: `{xp_min}-{xp_max}` XP."), ephemeral=True)

    @app_commands.command(name="config_economia", description="Configurar economia do servidor.")
    @app_commands.guild_only()
    async def config_economia(self, interaction: discord.Interaction, ativado: bool = True, nome_moeda: str = "moedas", daily: app_commands.Range[int, 1, 100000] = 500) -> None:
        if not await self._admin(interaction): return
        await self.bot.db.set_setting(interaction.guild_id, "economy.enabled", ativado)
        await self.bot.db.set_setting(interaction.guild_id, "economy.currency", nome_moeda[:32])
        await self.bot.db.set_setting(interaction.guild_id, "economy.daily", daily)
        await interaction.response.send_message(embed=sucesso_embed("Economia configurada", f"Ativada: `{ativado}`\nMoeda: `{nome_moeda[:32]}`\nDaily: `{daily}`."), ephemeral=True)

    @app_commands.command(name="config_ver", description="Ver configurações salvas do servidor.")
    @app_commands.guild_only()
    async def config_ver(self, interaction: discord.Interaction) -> None:
        if not await self._admin(interaction): return
        data = await self.bot.db.all_settings(interaction.guild_id)
        if not data:
            await interaction.response.send_message(embed=info_embed("Configurações", "Nenhuma configuração salva ainda."), ephemeral=True)
            return
        desc = "\n".join(f"`{k}` = `{str(v)[:80]}`" for k, v in sorted(data.items()))
        await interaction.response.send_message(embed=info_embed("Configurações do servidor", desc[:4000]), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Configuracao(bot))
