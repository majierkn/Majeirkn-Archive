"""Camada de acesso ao banco de dados (repository pattern) sobre aiosqlite."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/bot.db")
MIGRATIONS_DIR = "migrations"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class GuildSettings:
    guild_id: int
    dj_role_id: int | None = None
    default_volume: int = 100
    text_channel_id: int | None = None
    max_queue_size: int = 200
    language: str = "pt-BR"
    mode_247: bool = False
    crossfade_ms: int = 0
    inactivity_timeout_minutes: int = 5
    blocked_keywords: str = ""
    play_cooldown_seconds: int = 3


@dataclass
class Playlist:
    id: int
    guild_id: int | None
    owner_id: int
    name: str
    visibility: str
    created_at: str


@dataclass
class PlaylistTrack:
    id: int
    playlist_id: int
    title: str
    url: str
    duration_seconds: int | None
    thumbnail: str | None
    position: int


@dataclass
class PlayHistory:
    id: int
    guild_id: int
    user_id: int
    title: str
    url: str
    duration_seconds: int
    played_at: str


@dataclass
class TrackStat:
    url: str
    title: str
    play_count: int
    total_seconds: int


# ---------------------------------------------------------------------------
# Database manager
# ---------------------------------------------------------------------------


class Database:
    """Singleton de acesso ao banco SQLite assíncrono."""

    _instance: Database | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None

    @classmethod
    async def get(cls) -> Database:
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance._connect()
            return cls._instance

    async def _connect(self) -> None:
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        self._conn = await aiosqlite.connect(DB_PATH)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._run_migrations()

    async def _run_migrations(self) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await self._conn.commit()

        applied: set[int] = set()
        async with self._conn.execute("SELECT version FROM schema_version") as cur:
            async for row in cur:
                applied.add(row[0])

        if not os.path.isdir(MIGRATIONS_DIR):
            logger.warning("Pasta migrations/ não encontrada, pulando migrações.")
            return

        migration_files = sorted(
            f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
        )
        for fname in migration_files:
            try:
                version = int(fname.split("_")[0])
            except ValueError:
                continue
            if version in applied:
                continue
            path = os.path.join(MIGRATIONS_DIR, fname)
            with open(path, encoding="utf-8") as fh:
                sql = fh.read()
            await self._conn.executescript(sql)
            await self._conn.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (version,)
            )
            await self._conn.commit()
            logger.info("Migração aplicada: %s", fname)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    # ------------------------------------------------------------------
    # Guild settings
    # ------------------------------------------------------------------

    async def get_guild_settings(self, guild_id: int) -> GuildSettings:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            await self._conn.execute(
                "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
            )
            await self._conn.commit()
            return GuildSettings(guild_id=guild_id)
        return GuildSettings(
            guild_id=row["guild_id"],
            dj_role_id=row["dj_role_id"],
            default_volume=row["default_volume"],
            text_channel_id=row["text_channel_id"],
            max_queue_size=row["max_queue_size"],
            language=row["language"],
            mode_247=bool(row["mode_247"]),
            crossfade_ms=row["crossfade_ms"],
            inactivity_timeout_minutes=row["inactivity_timeout_minutes"],
            blocked_keywords=row["blocked_keywords"] or "",
            play_cooldown_seconds=row["play_cooldown_seconds"],
        )

    async def update_guild_settings(self, guild_id: int, **kwargs: Any) -> None:
        assert self._conn is not None
        if not kwargs:
            return
        columns = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [guild_id]
        await self._conn.execute(
            f"UPDATE guild_settings SET {columns} WHERE guild_id = ?", values
        )
        await self._conn.commit()

    async def ensure_guild(self, guild_id: int) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Blacklist
    # ------------------------------------------------------------------

    async def add_blacklist(self, guild_id: int, user_id: int, reason: str = "") -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT OR REPLACE INTO blacklist (guild_id, user_id, reason) VALUES (?, ?, ?)",
            (guild_id, user_id, reason),
        )
        await self._conn.commit()

    async def remove_blacklist(self, guild_id: int, user_id: int) -> bool:
        assert self._conn is not None
        cur = await self._conn.execute(
            "DELETE FROM blacklist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def is_blacklisted(self, guild_id: int, user_id: int) -> bool:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT 1 FROM blacklist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            return await cur.fetchone() is not None

    async def get_blacklist(self, guild_id: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT user_id, reason, added_at FROM blacklist WHERE guild_id = ?", (guild_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ------------------------------------------------------------------
    # Play history
    # ------------------------------------------------------------------

    async def add_history(
        self,
        guild_id: int,
        user_id: int,
        title: str,
        url: str,
        duration_seconds: int = 0,
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT INTO play_history (guild_id, user_id, title, url, duration_seconds) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, title, url, duration_seconds),
        )
        # Update stats
        await self._conn.execute(
            """INSERT INTO play_stats (guild_id, url, title, play_count, total_seconds)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT(guild_id, url) DO UPDATE SET
               play_count = play_count + 1,
               total_seconds = total_seconds + excluded.total_seconds,
               title = excluded.title""",
            (guild_id, url, title, duration_seconds),
        )
        await self._conn.execute(
            """INSERT INTO guild_play_totals (guild_id, total_tracks, total_seconds)
               VALUES (?, 1, ?)
               ON CONFLICT(guild_id) DO UPDATE SET
               total_tracks = total_tracks + 1,
               total_seconds = total_seconds + excluded.total_seconds""",
            (guild_id, duration_seconds),
        )
        await self._conn.commit()

    async def get_history(self, guild_id: int, limit: int = 20) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT title, url, user_id, played_at FROM play_history WHERE guild_id = ? ORDER BY played_at DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_top_tracks(self, guild_id: int, limit: int = 10) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT title, url, play_count, total_seconds FROM play_stats WHERE guild_id = ? ORDER BY play_count DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_guild_totals(self, guild_id: int) -> dict[str, int]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT total_tracks, total_seconds FROM guild_play_totals WHERE guild_id = ?",
            (guild_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return {"total_tracks": 0, "total_seconds": 0}
        return {"total_tracks": row["total_tracks"], "total_seconds": row["total_seconds"]}

    # ------------------------------------------------------------------
    # User data deletion (LGPD)
    # ------------------------------------------------------------------

    async def delete_user_data(self, user_id: int) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM play_history WHERE user_id = ?", (user_id,)
        )
        await self._conn.execute(
            "DELETE FROM playlists WHERE owner_id = ?", (user_id,)
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------

    async def create_playlist(
        self,
        owner_id: int,
        name: str,
        guild_id: int | None = None,
        visibility: str = "privada",
    ) -> int:
        assert self._conn is not None
        cur = await self._conn.execute(
            "INSERT INTO playlists (guild_id, owner_id, name, visibility) VALUES (?, ?, ?, ?)",
            (guild_id, owner_id, name, visibility),
        )
        await self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    async def get_playlist(
        self, owner_id: int, name: str, guild_id: int | None = None
    ) -> Playlist | None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM playlists WHERE owner_id = ? AND name = ?",
            (owner_id, name),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return Playlist(**dict(row))

    async def get_playlist_by_id(self, playlist_id: int) -> Playlist | None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return Playlist(**dict(row))

    async def list_playlists(self, owner_id: int) -> list[Playlist]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM playlists WHERE owner_id = ? ORDER BY name", (owner_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [Playlist(**dict(r)) for r in rows]

    async def list_public_playlists(self, guild_id: int) -> list[Playlist]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM playlists WHERE guild_id = ? AND visibility = 'publica' ORDER BY name",
            (guild_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [Playlist(**dict(r)) for r in rows]

    async def rename_playlist(self, playlist_id: int, new_name: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "UPDATE playlists SET name = ? WHERE id = ?", (new_name, playlist_id)
        )
        await self._conn.commit()

    async def delete_playlist(self, playlist_id: int) -> None:
        assert self._conn is not None
        await self._conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        await self._conn.commit()

    async def count_user_playlists(self, owner_id: int) -> int:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT COUNT(*) FROM playlists WHERE owner_id = ?", (owner_id,)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Playlist tracks
    # ------------------------------------------------------------------

    async def add_track_to_playlist(
        self,
        playlist_id: int,
        title: str,
        url: str,
        duration_seconds: int | None = None,
        thumbnail: str | None = None,
    ) -> None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT COALESCE(MAX(position), 0) FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,),
        ) as cur:
            row = await cur.fetchone()
        next_pos = (row[0] or 0) + 1
        await self._conn.execute(
            "INSERT INTO playlist_tracks (playlist_id, title, url, duration_seconds, thumbnail, position) VALUES (?, ?, ?, ?, ?, ?)",
            (playlist_id, title, url, duration_seconds, thumbnail, next_pos),
        )
        await self._conn.commit()

    async def get_playlist_tracks(self, playlist_id: int) -> list[PlaylistTrack]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM playlist_tracks WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [PlaylistTrack(**dict(r)) for r in rows]

    async def count_playlist_tracks(self, playlist_id: int) -> int:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,)
        ) as cur:
            row = await cur.fetchone()
        return row[0] if row else 0

    async def clear_playlist_tracks(self, playlist_id: int) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,)
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Persistent queue
    # ------------------------------------------------------------------

    async def save_queue(self, guild_id: int, tracks: list[dict[str, Any]]) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM persistent_queues WHERE guild_id = ?", (guild_id,)
        )
        for i, track in enumerate(tracks):
            await self._conn.execute(
                """INSERT INTO persistent_queues
                   (guild_id, position, title, url, duration_seconds, thumbnail, requested_by_id, requested_by_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    guild_id,
                    i,
                    track.get("title", ""),
                    track.get("url", ""),
                    track.get("duration_seconds"),
                    track.get("thumbnail"),
                    track.get("requested_by_id"),
                    track.get("requested_by_name"),
                ),
            )
        await self._conn.commit()

    async def load_queue(self, guild_id: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT * FROM persistent_queues WHERE guild_id = ? ORDER BY position",
            (guild_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def clear_queue(self, guild_id: int) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "DELETE FROM persistent_queues WHERE guild_id = ?", (guild_id,)
        )
        await self._conn.commit()
