"""Player de áudio: extração via yt-dlp e reprodução via FFmpeg."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import aiohttp
import discord

from core.queue_manager import Track

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração do yt-dlp
# ---------------------------------------------------------------------------

YTDL_OPTIONS: dict[str, Any] = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "skip_download": True,
    "age_limit": None,
}

YTDL_PLAYLIST_OPTIONS: dict[str, Any] = {
    **YTDL_OPTIONS,
    "extract_flat": True,
    "noplaylist": False,
}

FFMPEG_OPTIONS: dict[str, Any] = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# Filtros de áudio FFmpeg
AUDIO_FILTERS: dict[str, str] = {
    "bassboost": "bass=g=20,dynaudnorm=f=200",
    "nightcore": "asetrate=44100*1.25,aresample=44100,atempo=1.06",
    "vaporwave": "asetrate=44100*0.8,aresample=44100,atempo=0.9",
    "8d": "apulsator=hz=0.08",
    "karaoke": "stereotools=mleft=-0.1:mright=-0.1:sleft=1:sright=1",
    "tremolo": "tremolo=f=4:d=0.5",
    "vibrato": "vibrato=f=7:d=0.5",
    "normalizer": "dynaudnorm=f=150:g=15",
}


class ExtractionError(Exception):
    """Erro durante a extração de informações do yt-dlp."""


class PlayerState:
    """Estado de um player de servidor."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.paused_at: float | None = None
        self.paused_duration: float = 0.0
        self.current_position_offset: int = 0  # para /seek
        self.active_filters: dict[str, bool] = {}
        self.equalizer_bands: dict[str, float] = {}
        self.volume: float = 1.0
        self.sleep_timer_task: asyncio.Task[None] | None = None
        self.nowplaying_message: discord.Message | None = None
        self.progress_task: asyncio.Task[None] | None = None
        self.inactivity_task: asyncio.Task[None] | None = None

    @property
    def elapsed_seconds(self) -> int:
        if self.start_time == 0:
            return 0
        if self.paused_at is not None:
            return int(self.paused_at - self.start_time - self.paused_duration) + self.current_position_offset
        return int(time.monotonic() - self.start_time - self.paused_duration) + self.current_position_offset

    def on_play(self, position_offset: int = 0) -> None:
        self.start_time = time.monotonic()
        self.paused_duration = 0.0
        self.paused_at = None
        self.current_position_offset = position_offset

    def on_pause(self) -> None:
        if self.paused_at is None:
            self.paused_at = time.monotonic()

    def on_resume(self) -> None:
        if self.paused_at is not None:
            self.paused_duration += time.monotonic() - self.paused_at
            self.paused_at = None

    def build_filter_string(self) -> str | None:
        parts: list[str] = []
        for name, enabled in self.active_filters.items():
            if enabled and name in AUDIO_FILTERS:
                parts.append(AUDIO_FILTERS[name])
        for band, gain in self.equalizer_bands.items():
            parts.append(f"equalizer=f={band}:width_type=o:width=1:g={gain:.1f}")
        return ",".join(parts) if parts else None

    def build_ffmpeg_options(self, seek_seconds: int = 0) -> dict[str, Any]:
        before_opts = FFMPEG_OPTIONS["before_options"]
        if seek_seconds > 0:
            before_opts = f"-ss {seek_seconds} " + before_opts
        opts = FFMPEG_OPTIONS["options"]
        filter_str = self.build_filter_string()
        if filter_str:
            opts += f" -af {filter_str}"
        volume_filter = f"volume={self.volume:.2f}"
        if filter_str:
            opts += f",{volume_filter}"
        else:
            opts += f" -af {volume_filter}"
        return {"before_options": before_opts, "options": opts}


# Global player states per guild
_player_states: dict[int, PlayerState] = {}


def get_player_state(guild_id: int) -> PlayerState:
    if guild_id not in _player_states:
        _player_states[guild_id] = PlayerState()
    return _player_states[guild_id]


def remove_player_state(guild_id: int) -> None:
    _player_states.pop(guild_id, None)


# ---------------------------------------------------------------------------
# SponsorBlock integration
# ---------------------------------------------------------------------------

SPONSORBLOCK_API = "https://sponsor.ajay.app/api/skipSegments"


async def get_sponsor_segments(video_id: str) -> list[tuple[float, float]]:
    """Busca segmentos de patrocínio via SponsorBlock."""
    try:
        # Hash SHA-256 prefix (4 chars) do videoID para privacidade
        import hashlib
        prefix = hashlib.sha256(video_id.encode()).hexdigest()[:4]
        url = f"https://sponsor.ajay.app/api/skipSegments/{prefix}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                segments: list[tuple[float, float]] = []
                for item in data:
                    if item.get("videoID") == video_id:
                        for seg in item.get("segments", []):
                            if seg.get("category") in {"sponsor", "intro", "outro", "selfpromo"}:
                                segments.append((seg["segment"][0], seg["segment"][1]))
                return segments
    except Exception:
        return []


# ---------------------------------------------------------------------------
# yt-dlp extraction
# ---------------------------------------------------------------------------


async def extract_info(
    query: str,
    *,
    playlist: bool = False,
    loop: asyncio.AbstractEventLoop | None = None,
) -> dict[str, Any]:
    """
    Extrai informações de uma URL ou busca. Roda em thread separada para não bloquear.

    Levanta ExtractionError com mensagem amigável em caso de falha.
    """
    import yt_dlp

    opts = YTDL_PLAYLIST_OPTIONS if playlist else YTDL_OPTIONS

    def _extract() -> dict[str, Any]:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(query, download=False)  # type: ignore[return-value]

    if loop is None:
        loop = asyncio.get_event_loop()

    try:
        data = await loop.run_in_executor(None, _extract)
    except Exception as exc:
        msg = str(exc).lower()
        if "private" in msg or "unavailable" in msg:
            raise ExtractionError("❌ Este vídeo é privado ou foi removido.") from exc
        if "age" in msg or "sign in" in msg:
            raise ExtractionError(
                "❌ Este conteúdo tem restrição de idade e não pode ser reproduzido."
            ) from exc
        if "blocked" in msg or "not available in your country" in msg:
            raise ExtractionError(
                "❌ Este conteúdo não está disponível na região do servidor."
            ) from exc
        if "live" in msg:
            raise ExtractionError(
                "❌ Streams ao vivo não suportam /seek. Use /play para reiniciar."
            ) from exc
        raise ExtractionError(f"❌ Não foi possível reproduzir: {exc}") from exc

    if data is None:
        raise ExtractionError("❌ Nenhum resultado encontrado.")

    return data


async def resolve_audio_url(webpage_url: str) -> str:
    """Resolve a URL de streaming de áudio a partir da URL da página."""
    import yt_dlp

    def _get_url() -> str:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(webpage_url, download=False)
            if info is None:
                raise ExtractionError("Não foi possível resolver a URL de áudio.")
            formats = info.get("formats", [info])
            # Pegar melhor formato de áudio
            audio_formats = [
                f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"
            ]
            if audio_formats:
                return audio_formats[-1]["url"]
            return formats[-1]["url"]

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _get_url)
    except Exception as exc:
        raise ExtractionError(f"Erro ao resolver URL de áudio: {exc}") from exc


async def search_youtube(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Busca no YouTube e retorna até max_results resultados."""
    import yt_dlp

    search_query = f"ytsearch{max_results}:{query}"
    opts = {**YTDL_OPTIONS, "extract_flat": True}

    def _search() -> list[dict[str, Any]]:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(search_query, download=False)
            if data is None:
                return []
            return data.get("entries", [])

    try:
        results = await asyncio.get_event_loop().run_in_executor(None, _search)
        return [r for r in results if r is not None][:max_results]
    except Exception:
        return []


async def resolve_spotify(url: str) -> list[dict[str, Any]]:
    """
    Resolve metadados do Spotify e retorna itens para busca no YouTube.
    Como Spotify não permite streaming, buscamos o equivalente no YouTube.
    """
    # Extraímos via yt-dlp que suporta Spotify via spotdl/spotbeach internamente
    try:
        data = await extract_info(url, playlist="playlist" in url or "album" in url)
        if data.get("_type") == "playlist":
            return [e for e in data.get("entries", []) if e]
        return [data]
    except ExtractionError:
        return []


def make_ffmpeg_source(
    audio_url: str,
    state: PlayerState,
    seek_seconds: int = 0,
) -> discord.FFmpegPCMAudio:
    """Cria uma fonte de áudio FFmpeg."""
    opts = state.build_ffmpeg_options(seek_seconds)
    return discord.FFmpegPCMAudio(audio_url, **opts)


def make_volume_source(
    source: discord.FFmpegPCMAudio,
    volume: float,
) -> discord.PCMVolumeTransformer:
    """Envolve a fonte com controle de volume."""
    return discord.PCMVolumeTransformer(source, volume=volume)
