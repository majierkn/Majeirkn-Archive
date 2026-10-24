"""Funções auxiliares diversas."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import discord


def progress_bar(current: int, total: int, length: int = 20) -> str:
    """Gera uma barra de progresso em texto."""
    if total <= 0:
        return "▬" * length
    filled = int(length * current / total)
    filled = min(filled, length)
    bar = "━" * filled + "🔘" + "─" * (length - filled - 1)
    return bar


def truncate(text: str, max_length: int = 50) -> str:
    """Trunca um texto com reticências se necessário."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def is_url(text: str) -> bool:
    """Verifica se o texto é uma URL."""
    pattern = re.compile(
        r"^(?:http|ftp)s?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(pattern.match(text))


def is_spotify_url(url: str) -> bool:
    return "open.spotify.com" in url or "spotify.com" in url


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def is_soundcloud_url(url: str) -> bool:
    return "soundcloud.com" in url


def is_playlist_url(url: str) -> bool:
    return "playlist" in url or "album" in url or "/sets/" in url


async def safe_delete_message(message: discord.Message, delay: float = 0) -> None:
    """Deleta uma mensagem silenciosamente."""
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        pass


def member_voice_count(voice_channel: discord.VoiceChannel) -> int:
    """Conta membros humanos em um canal de voz."""
    return sum(1 for m in voice_channel.members if not m.bot)


def chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    """Divide uma lista em sublistas de tamanho fixo."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


SPOTIFY_TRACK_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([A-Za-z0-9]+)"
)
SPOTIFY_PLAYLIST_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?playlist/([A-Za-z0-9]+)"
)
SPOTIFY_ALBUM_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?album/([A-Za-z0-9]+)"
)
YOUTUBE_VIDEO_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})"
)
