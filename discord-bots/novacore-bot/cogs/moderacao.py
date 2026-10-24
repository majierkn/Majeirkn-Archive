from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_bot_permissions, require_permissions, validate_member_moderation, validate_role_management
from utils.embeds import aviso_embed, enviar_log, erro_embed, info_embed, sucesso_embed
from utils.time import parse_duration, human_timedelta


class Moderacao(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="banir", description="Banir um membro do servidor.")
    @app_commands.guild_only()
    async def banir(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, ban_members=True): return
        if not await require_bot_permissions(interaction, ban_members=True): return
        if not await validate_member_moderation(interaction, membro): return
        await membro.ban(reason=f"{motivo} | Moderador: {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Membro banido", f"{membro.mention} foi banido.\nMotivo: `{motivo}`"))
        await enviar_log(self.bot, interaction.guild, "🔨 Punição: ban", f"Usuário: {membro.mention}\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0xE74C3C)

    @app_commands.command(name="desbanir", description="Desbanir um usuário pelo ID.")
    @app_commands.guild_only()
    async def desbanir(self, interaction: discord.Interaction, user_id: str, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, ban_members=True): return
        if not await require_bot_permissions(interaction, ban_members=True): return
        try:
            user = await self.bot.fetch_user(int(user_id))
        except Exception:
            await interaction.response.send_message(embed=erro_embed("ID inválido", "Informe um ID de usuário válido."), ephemeral=True)
            return
        await interaction.guild.unban(user, reason=f"{motivo} | Moderador: {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Usuário desbanido", f"`{user}` foi desbanido."))
        await enviar_log(self.bot, interaction.guild, "✅ Punição removida: unban", f"Usuário: `{user}` (`{user.id}`)\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0x2ECC71)

    @app_commands.command(name="expulsar", description="Expulsar um membro do servidor.")
    @app_commands.guild_only()
    async def expulsar(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, kick_members=True): return
        if not await require_bot_permissions(interaction, kick_members=True): return
        if not await validate_member_moderation(interaction, membro): return
        await membro.kick(reason=f"{motivo} | Moderador: {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Membro expulso", f"{membro.mention} foi expulso.\nMotivo: `{motivo}`"))
        await enviar_log(self.bot, interaction.guild, "👢 Punição: kick", f"Usuário: {membro.mention}\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0xE67E22)

    @app_commands.command(name="castigar", description="Aplicar timeout/castigo em um membro.")
    @app_commands.guild_only()
    async def castigar(self, interaction: discord.Interaction, membro: discord.Member, duracao: str, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, moderate_members=True): return
        if not await require_bot_permissions(interaction, moderate_members=True): return
        if not await validate_member_moderation(interaction, membro): return
        try:
            delta = parse_duration(duracao)
        except ValueError as exc:
            await interaction.response.send_message(embed=erro_embed("Duração inválida", str(exc)), ephemeral=True)
            return
        until = datetime.now(timezone.utc) + delta
        await membro.timeout(until, reason=f"{motivo} | Moderador: {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Membro castigado", f"{membro.mention} recebeu castigo por `{human_timedelta(delta)}`.\nMotivo: `{motivo}`"))
        await enviar_log(self.bot, interaction.guild, "⏳ Punição: castigo", f"Usuário: {membro.mention}\nTempo: {human_timedelta(delta)}\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0xF1C40F)

    @app_commands.command(name="remover_castigo", description="Remover timeout/castigo de um membro.")
    @app_commands.guild_only()
    async def remover_castigo(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, moderate_members=True): return
        if not await require_bot_permissions(interaction, moderate_members=True): return
        if not await validate_member_moderation(interaction, membro): return
        await membro.timeout(None, reason=f"{motivo} | Moderador: {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Castigo removido", f"O castigo de {membro.mention} foi removido."))
        await enviar_log(self.bot, interaction.guild, "✅ Castigo removido", f"Usuário: {membro.mention}\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0x2ECC71)

    @app_commands.command(name="avisar", description="Registrar um aviso contra um membro.")
    @app_commands.guild_only()
    async def avisar(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = "Não informado") -> None:
        if not await require_permissions(interaction, moderate_members=True): return
        if not await validate_member_moderation(interaction, membro): return
        warning_id = await self.bot.db.add_warning(interaction.guild_id, membro.id, interaction.user.id, motivo)
        await interaction.response.send_message(embed=aviso_embed("Aviso registrado", f"Aviso `#{warning_id}` para {membro.mention}.\nMotivo: `{motivo}`"))
        await enviar_log(self.bot, interaction.guild, "⚠️ Aviso", f"Usuário: {membro.mention}\nModerador: {interaction.user.mention}\nMotivo: {motivo}", 0xF1C40F)

    @app_commands.command(name="avisos", description="Ver avisos de um membro.")
    @app_commands.guild_only()
    async def avisos(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        if not await require_permissions(interaction, moderate_members=True): return
        rows = await self.bot.db.get_warnings(interaction.guild_id, membro.id)
        if not rows:
            await interaction.response.send_message(embed=info_embed("Sem avisos", f"{membro.mention} não possui avisos."), ephemeral=True)
            return
        desc = "\n".join(f"`#{r['id']}` <t:{r['created_at']}:d> — {r['motivo']}" for r in rows[:15])
        await interaction.response.send_message(embed=info_embed(f"Avisos de {membro}", desc), ephemeral=True)

    @app_commands.command(name="remover_aviso", description="Remover um aviso pelo ID.")
    @app_commands.guild_only()
    async def remover_aviso(self, interaction: discord.Interaction, aviso_id: int) -> None:
        if not await require_permissions(interaction, moderate_members=True): return
        ok = await self.bot.db.remove_warning(interaction.guild_id, aviso_id)
        embed = sucesso_embed("Aviso removido", f"Aviso `#{aviso_id}` removido.") if ok else erro_embed("Não encontrado", "Não encontrei esse aviso neste servidor.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="limpar", description="Apagar mensagens de um canal.")
    @app_commands.guild_only()
    async def limpar(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]) -> None:
        if not await require_permissions(interaction, manage_messages=True): return
        if not await require_bot_permissions(interaction, manage_messages=True): return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(embed=sucesso_embed("Mensagens limpas", f"Foram apagadas `{len(deleted)}` mensagens."), ephemeral=True)
        await enviar_log(self.bot, interaction.guild, "🧹 Limpeza de mensagens", f"Canal: {interaction.channel.mention}\nModerador: {interaction.user.mention}\nQuantidade: {len(deleted)}", 0x3498DB)

    @app_commands.command(name="trancar", description="Trancar o canal atual ou informado.")
    @app_commands.guild_only()
    async def trancar(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not await require_bot_permissions(interaction, manage_channels=True): return
        canal = canal or interaction.channel
        await canal.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(embed=sucesso_embed("Canal trancado", f"{canal.mention} foi trancado."))

    @app_commands.command(name="destrancar", description="Destrancar o canal atual ou informado.")
    @app_commands.guild_only()
    async def destrancar(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not await require_bot_permissions(interaction, manage_channels=True): return
        canal = canal or interaction.channel
        await canal.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(embed=sucesso_embed("Canal destrancado", f"{canal.mention} foi destrancado."))

    @app_commands.command(name="modo_lento", description="Definir modo lento no canal.")
    @app_commands.guild_only()
    async def modo_lento(self, interaction: discord.Interaction, segundos: app_commands.Range[int, 0, 21600], canal: Optional[discord.TextChannel] = None) -> None:
        if not await require_permissions(interaction, manage_channels=True): return
        if not await require_bot_permissions(interaction, manage_channels=True): return
        canal = canal or interaction.channel
        await canal.edit(slowmode_delay=segundos)
        await interaction.response.send_message(embed=sucesso_embed("Modo lento atualizado", f"{canal.mention}: `{segundos}s`."))

    @app_commands.command(name="nick", description="Alterar apelido de um membro.")
    @app_commands.guild_only()
    async def nick(self, interaction: discord.Interaction, membro: discord.Member, novo_nick: str) -> None:
        if not await require_permissions(interaction, manage_nicknames=True): return
        if not await require_bot_permissions(interaction, manage_nicknames=True): return
        if not await validate_member_moderation(interaction, membro): return
        await membro.edit(nick=novo_nick[:32], reason=f"Alterado por {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Nick alterado", f"Novo nick de {membro.mention}: `{novo_nick[:32]}`."))

    @app_commands.command(name="cargo_adicionar", description="Adicionar cargo a um membro.")
    @app_commands.guild_only()
    async def cargo_adicionar(self, interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role) -> None:
        if not await require_permissions(interaction, manage_roles=True): return
        if not await require_bot_permissions(interaction, manage_roles=True): return
        if not await validate_role_management(interaction, cargo): return
        await membro.add_roles(cargo, reason=f"Adicionado por {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Cargo adicionado", f"{cargo.mention} foi adicionado a {membro.mention}."))

    @app_commands.command(name="cargo_remover", description="Remover cargo de um membro.")
    @app_commands.guild_only()
    async def cargo_remover(self, interaction: discord.Interaction, membro: discord.Member, cargo: discord.Role) -> None:
        if not await require_permissions(interaction, manage_roles=True): return
        if not await require_bot_permissions(interaction, manage_roles=True): return
        if not await validate_role_management(interaction, cargo): return
        await membro.remove_roles(cargo, reason=f"Removido por {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Cargo removido", f"{cargo.mention} foi removido de {membro.mention}."))

    @app_commands.command(name="anunciar", description="Enviar anúncio em embed.")
    @app_commands.guild_only()
    async def anunciar(self, interaction: discord.Interaction, canal: discord.TextChannel, titulo: str, mensagem: str) -> None:
        if not await require_permissions(interaction, manage_messages=True): return
        embed = info_embed(titulo[:256], mensagem[:4000])
        await canal.send(embed=embed)
        await interaction.response.send_message(embed=sucesso_embed("Anúncio enviado", f"Mensagem enviada em {canal.mention}."), ephemeral=True)

    @app_commands.command(name="falar", description="Fazer o bot enviar uma mensagem simples.")
    @app_commands.guild_only()
    async def falar(self, interaction: discord.Interaction, canal: discord.TextChannel, mensagem: str) -> None:
        if not await require_permissions(interaction, manage_messages=True): return
        await canal.send(mensagem[:1900])
        await interaction.response.send_message(embed=sucesso_embed("Mensagem enviada", f"Enviado em {canal.mention}."), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderacao(bot))
