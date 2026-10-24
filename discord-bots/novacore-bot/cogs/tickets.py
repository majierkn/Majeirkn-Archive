from __future__ import annotations

import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_bot_permissions, require_permissions
from utils.embeds import enviar_log, erro_embed, info_embed, sucesso_embed


class TicketView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Abrir ticket", style=discord.ButtonStyle.primary, custom_id="novacore:open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Use isso em um servidor.", ephemeral=True)
            return
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.id}")
        if existing:
            await interaction.response.send_message(embed=erro_embed("Ticket já aberto", f"Você já possui um ticket: {existing.mention}"), ephemeral=True)
            return

        category_id = await self.bot.db.get_setting(guild.id, "tickets.category_id")
        support_role_id = await self.bot.db.get_setting(guild.id, "tickets.support_role_id")
        category = guild.get_channel(int(category_id)) if category_id else None
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason=f"Ticket aberto por {interaction.user}",
        )
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO tickets (guild_id, channel_id, user_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild.id, channel.id, interaction.user.id, "aberto", int(time.time())),
        )
        await channel.send(embed=info_embed("Ticket aberto", f"{interaction.user.mention}, explique seu problema. A equipe responderá em breve."))
        await interaction.response.send_message(embed=sucesso_embed("Ticket criado", f"Seu ticket foi criado: {channel.mention}"), ephemeral=True)
        await enviar_log(self.bot, guild, "🎫 Ticket aberto", f"Usuário: {interaction.user.mention}\nCanal: {channel.mention}", 0x3498DB)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.add_view(TicketView(bot))

    @app_commands.command(name="painel_ticket", description="Enviar painel de tickets com botão.")
    @app_commands.guild_only()
    async def painel_ticket(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        if not await require_bot_permissions(interaction, manage_channels=True): return
        canal = canal or interaction.channel
        embed = info_embed("Central de Atendimento", "Clique no botão abaixo para abrir um ticket privado com a equipe.")
        await canal.send(embed=embed, view=TicketView(self.bot))
        await interaction.response.send_message(embed=sucesso_embed("Painel enviado", f"Painel enviado em {canal.mention}."), ephemeral=True)

    def _is_ticket(self, channel: discord.abc.GuildChannel) -> bool:
        return isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-")

    @app_commands.command(name="fechar_ticket", description="Fechar o ticket atual.")
    @app_commands.guild_only()
    async def fechar_ticket(self, interaction: discord.Interaction, motivo: str = "Resolvido") -> None:
        if not self._is_ticket(interaction.channel):
            await interaction.response.send_message(embed=erro_embed("Canal inválido", "Use este comando dentro de um ticket."), ephemeral=True)
            return
        await interaction.response.send_message(embed=sucesso_embed("Ticket fechado", "Este canal será removido em alguns segundos."))
        await self.bot.db.execute("UPDATE tickets SET status='fechado' WHERE channel_id=?", (interaction.channel.id,))
        await enviar_log(self.bot, interaction.guild, "🎫 Ticket fechado", f"Canal: `{interaction.channel.name}`\nPor: {interaction.user.mention}\nMotivo: {motivo}", 0xE74C3C)
        await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}: {motivo}")

    @app_commands.command(name="adicionar_ticket", description="Adicionar membro ao ticket atual.")
    @app_commands.guild_only()
    async def adicionar_ticket(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not self._is_ticket(interaction.channel):
            await interaction.response.send_message(embed=erro_embed("Canal inválido", "Use este comando dentro de um ticket."), ephemeral=True)
            return
        await interaction.channel.set_permissions(membro, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(embed=sucesso_embed("Membro adicionado", f"{membro.mention} foi adicionado ao ticket."))

    @app_commands.command(name="remover_ticket", description="Remover membro do ticket atual.")
    @app_commands.guild_only()
    async def remover_ticket(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not self._is_ticket(interaction.channel):
            await interaction.response.send_message(embed=erro_embed("Canal inválido", "Use este comando dentro de um ticket."), ephemeral=True)
            return
        await interaction.channel.set_permissions(membro, overwrite=None)
        await interaction.response.send_message(embed=sucesso_embed("Membro removido", f"{membro.mention} foi removido do ticket."))

    @app_commands.command(name="renomear_ticket", description="Renomear o ticket atual.")
    @app_commands.guild_only()
    async def renomear_ticket(self, interaction: discord.Interaction, nome: str) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not self._is_ticket(interaction.channel):
            await interaction.response.send_message(embed=erro_embed("Canal inválido", "Use este comando dentro de um ticket."), ephemeral=True)
            return
        safe = "ticket-" + "".join(c for c in nome.lower().replace(" ", "-") if c.isalnum() or c == "-")[:80]
        await interaction.channel.edit(name=safe)
        await interaction.response.send_message(embed=sucesso_embed("Ticket renomeado", f"Novo nome: `{safe}`."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
