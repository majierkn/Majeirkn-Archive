from __future__ import annotations

import discord
from discord import app_commands

from utils.embeds import erro_embed


def guild_only(interaction: discord.Interaction) -> discord.Guild:
    if interaction.guild is None:
        raise app_commands.CheckFailure("Este comando só pode ser usado em servidor.")
    return interaction.guild


async def require_permissions(interaction: discord.Interaction, **perms: bool) -> bool:
    guild = guild_only(interaction)
    member = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
    if not isinstance(member, discord.Member):
        await interaction.response.send_message(embed=erro_embed("Erro", "Não consegui validar suas permissões."), ephemeral=True)
        return False
    permissions = member.guild_permissions
    missing = [name for name, value in perms.items() if value and not getattr(permissions, name, False)]
    if missing:
        await interaction.response.send_message(
            embed=erro_embed("Permissão insuficiente", f"Você precisa das permissões: `{', '.join(missing)}`."),
            ephemeral=True,
        )
        return False
    return True


async def require_bot_permissions(interaction: discord.Interaction, **perms: bool) -> bool:
    guild = guild_only(interaction)
    me = guild.me
    if me is None:
        await interaction.response.send_message(embed=erro_embed("Erro", "Não consegui validar minhas permissões."), ephemeral=True)
        return False
    permissions = me.guild_permissions
    missing = [name for name, value in perms.items() if value and not getattr(permissions, name, False)]
    if missing:
        await interaction.response.send_message(
            embed=erro_embed("Permissões do bot", f"Eu preciso das permissões: `{', '.join(missing)}`."),
            ephemeral=True,
        )
        return False
    return True


def can_moderate(actor: discord.Member, target: discord.Member) -> tuple[bool, str]:
    if actor.id == target.id:
        return False, "Você não pode executar moderação contra si mesmo."
    if actor.guild.owner_id == actor.id:
        return True, ""
    if target.guild.owner_id == target.id:
        return False, "Você não pode moderar o dono do servidor."
    if actor.top_role <= target.top_role:
        return False, "O cargo do alvo é maior ou igual ao seu."
    return True, ""


def bot_can_moderate(bot_member: discord.Member, target: discord.Member) -> tuple[bool, str]:
    if target.guild.owner_id == target.id:
        return False, "Eu não posso moderar o dono do servidor."
    if bot_member.top_role <= target.top_role:
        return False, "Meu cargo precisa ficar acima do cargo do alvo."
    return True, ""


async def validate_member_moderation(interaction: discord.Interaction, target: discord.Member) -> bool:
    guild = guild_only(interaction)
    actor = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
    me = guild.me
    if not isinstance(actor, discord.Member) or me is None:
        await interaction.response.send_message(embed=erro_embed("Erro", "Não consegui validar hierarquia de cargos."), ephemeral=True)
        return False
    ok, reason = can_moderate(actor, target)
    if not ok:
        await interaction.response.send_message(embed=erro_embed("Ação bloqueada", reason), ephemeral=True)
        return False
    ok, reason = bot_can_moderate(me, target)
    if not ok:
        await interaction.response.send_message(embed=erro_embed("Ação bloqueada", reason), ephemeral=True)
        return False
    return True


async def validate_role_management(interaction: discord.Interaction, role: discord.Role) -> bool:
    guild = guild_only(interaction)
    actor = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
    me = guild.me
    if not isinstance(actor, discord.Member) or me is None:
        await interaction.response.send_message(embed=erro_embed("Erro", "Não consegui validar hierarquia de cargos."), ephemeral=True)
        return False
    if role >= actor.top_role and guild.owner_id != actor.id:
        await interaction.response.send_message(embed=erro_embed("Ação bloqueada", "Esse cargo é maior ou igual ao seu."), ephemeral=True)
        return False
    if role >= me.top_role:
        await interaction.response.send_message(embed=erro_embed("Ação bloqueada", "Esse cargo é maior ou igual ao meu."), ephemeral=True)
        return False
    return True
