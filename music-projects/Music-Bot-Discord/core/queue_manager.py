"""Gerenciador de fila de músicas por servidor."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoopMode(Enum):
    OFF = "off"
    TRACK = "track"
    QUEUE = "queue"


@dataclass
class Track:
    """Representa uma faixa na fila."""

    title: str
    url: str
    webpage_url: str = ""
    duration_seconds: int = 0
    thumbnail: str | None = None
    requested_by_id: int = 0
    requested_by_name: str = ""
    uploader: str = ""
    source_type: str = "youtube"  # youtube, spotify, soundcloud, direct, etc.
    is_stream: bool = False
    audio_url: str = ""  # URL de streaming resolvida

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "webpage_url": self.webpage_url,
            "duration_seconds": self.duration_seconds,
            "thumbnail": self.thumbnail,
            "requested_by_id": self.requested_by_id,
            "requested_by_name": self.requested_by_name,
            "uploader": self.uploader,
            "source_type": self.source_type,
            "is_stream": self.is_stream,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Track:
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            webpage_url=data.get("webpage_url", ""),
            duration_seconds=data.get("duration_seconds", 0),
            thumbnail=data.get("thumbnail"),
            requested_by_id=data.get("requested_by_id", 0),
            requested_by_name=data.get("requested_by_name", ""),
            uploader=data.get("uploader", ""),
            source_type=data.get("source_type", "youtube"),
            is_stream=data.get("is_stream", False),
        )

    @classmethod
    def from_ytdlp(cls, data: dict[str, Any], requested_by_id: int = 0, requested_by_name: str = "") -> Track:
        return cls(
            title=data.get("title", "Sem título"),
            url=data.get("webpage_url") or data.get("url", ""),
            webpage_url=data.get("webpage_url") or data.get("url", ""),
            duration_seconds=int(data.get("duration") or 0),
            thumbnail=data.get("thumbnail"),
            requested_by_id=requested_by_id,
            requested_by_name=requested_by_name,
            uploader=data.get("uploader") or data.get("channel") or "",
            source_type="stream" if data.get("is_live") else "youtube",
            is_stream=bool(data.get("is_live")),
        )


class QueueManager:
    """Gerencia a fila de um servidor específico."""

    def __init__(self, guild_id: int, max_size: int = 200) -> None:
        self.guild_id = guild_id
        self.max_size = max_size
        self._queue: list[Track] = []
        self._history: list[Track] = []
        self._current: Track | None = None
        self.loop_mode: LoopMode = LoopMode.OFF
        self.autoplay: bool = False
        self._lock = asyncio.Lock()

    @property
    def current(self) -> Track | None:
        return self._current

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    @property
    def history(self) -> list[Track]:
        return list(self._history[-20:])

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self.max_size

    async def add(self, track: Track) -> bool:
        """Adiciona uma faixa. Retorna False se a fila estiver cheia."""
        async with self._lock:
            if self.is_full:
                return False
            self._queue.append(track)
            return True

    async def add_many(self, tracks: list[Track]) -> int:
        """Adiciona múltiplas faixas. Retorna o número adicionado."""
        added = 0
        async with self._lock:
            for track in tracks:
                if self.is_full:
                    break
                self._queue.append(track)
                added += 1
        return added

    async def next(self) -> Track | None:
        """Avança para a próxima faixa respeitando o modo de loop."""
        async with self._lock:
            if self._current is not None:
                self._history.append(self._current)
                if len(self._history) > 50:
                    self._history = self._history[-50:]

            if self.loop_mode == LoopMode.TRACK and self._current is not None:
                return self._current

            if self.loop_mode == LoopMode.QUEUE and self._current is not None:
                self._queue.append(self._current)

            if not self._queue:
                self._current = None
                return None

            self._current = self._queue.pop(0)
            return self._current

    async def previous(self) -> Track | None:
        """Volta para a faixa anterior do histórico."""
        async with self._lock:
            if not self._history:
                return None
            prev = self._history.pop()
            if self._current is not None:
                self._queue.insert(0, self._current)
            self._current = prev
            return prev

    async def skip(self) -> Track | None:
        """Pula a faixa atual (ignora modo de loop)."""
        async with self._lock:
            if self._current is not None:
                self._history.append(self._current)
                if len(self._history) > 50:
                    self._history = self._history[-50:]
            if not self._queue:
                self._current = None
                return None
            self._current = self._queue.pop(0)
            return self._current

    async def clear(self) -> None:
        async with self._lock:
            self._queue.clear()
            self._current = None

    async def shuffle(self) -> None:
        async with self._lock:
            random.shuffle(self._queue)

    async def remove(self, position: int) -> Track | None:
        """Remove faixa na posição (1-indexed). Retorna a faixa removida ou None."""
        async with self._lock:
            idx = position - 1
            if idx < 0 or idx >= len(self._queue):
                return None
            return self._queue.pop(idx)

    async def move(self, from_pos: int, to_pos: int) -> bool:
        """Move faixa de uma posição para outra (1-indexed)."""
        async with self._lock:
            fi, ti = from_pos - 1, to_pos - 1
            n = len(self._queue)
            if not (0 <= fi < n and 0 <= ti < n):
                return False
            track = self._queue.pop(fi)
            self._queue.insert(ti, track)
            return True

    def load_from_dicts(self, tracks: list[dict[str, Any]]) -> None:
        """Restaura a fila a partir de dados serializados (persistência)."""
        self._queue = [Track.from_dict(t) for t in tracks]

    def to_dicts(self) -> list[dict[str, Any]]:
        """Serializa a fila para persistência."""
        return [t.to_dict() for t in self._queue]


class QueueRegistry:
    """Registro global de filas por servidor."""

    def __init__(self) -> None:
        self._queues: dict[int, QueueManager] = {}

    def get(self, guild_id: int, max_size: int = 200) -> QueueManager:
        if guild_id not in self._queues:
            self._queues[guild_id] = QueueManager(guild_id, max_size)
        return self._queues[guild_id]

    def remove(self, guild_id: int) -> None:
        self._queues.pop(guild_id, None)

    def update_max_size(self, guild_id: int, max_size: int) -> None:
        if guild_id in self._queues:
            self._queues[guild_id].max_size = max_size


# Singleton global
queue_registry = QueueRegistry()
