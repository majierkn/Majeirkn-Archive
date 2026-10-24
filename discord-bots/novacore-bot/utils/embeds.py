from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR = 0xE74C3C
COLOR_INFO = 0x3498DB
COLOR_WARNING = 0xF1C40F
COLOR_DEFAULT = 0x5865F2


def base_embed(titulo: str, descricao: str | None = None, color: int = COLOR_DEFAULT) -> discord.Embed:
    embed = discord.Embed(title=titulo, description=descricao, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_footer(text="NovaCore Bot")
    return embed


def sucesso_embed(titulo: str, descricao: str | None = None) -> discord.Embed:
    return base_embed(f"✅ {titulo}", descricao, COLOR_SUCCESS)


def erro_embed(titulo: str, descricao: str | None = None) -> discord.Embed:
    return base_embed(f"❌ {titulo}", descricao, COLOR_ERROR)


def aviso_embed(titulo: str, descricao: str | None = None) -> discord.Embed:
    return base_embed(f"⚠️ {titulo}", descricao, COLOR_WARNING)


def info_embed(titulo: str, descricao: str | None = None) -> discord.Embed:
    return base_embed(f"ℹ️ {titulo}", descricao, COLOR_INFO)


async def enviar_log(bot: discord.Client, guild: discord.Guild, titulo: str, descricao: str, color: int = COLOR_DEFAULT) -> None:
    db = getattr(bot, "db", None)
    if db is None:
        return
    canal_id = await db.get_setting(guild.id, "logs.canal_id")
    if not canal_id:
        return
    canal = guild.get_channel(int(canal_id))
    if not isinstance(canal, discord.TextChannel):
        return
    embed = base_embed(titulo, descricao, color)
    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        return


def user_line(user: discord.abc.User) -> str:
    return f"{user.mention} (`{user.id}`)"


def channel_line(channel: Optional[discord.abc.GuildChannel]) -> str:
    if channel is None:
        return "Canal desconhecido"
    return f"{channel.mention} (`{channel.id}`)" if hasattr(channel, "mention") else f"{channel.name} (`{channel.id}`)"
