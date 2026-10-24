"""Testes para o módulo core/queue_manager.py."""

import pytest

from core.queue_manager import LoopMode, QueueManager, Track


def make_track(title: str, url: str = "https://example.com") -> Track:
    return Track(title=title, url=url, webpage_url=url, duration_seconds=180)


@pytest.mark.asyncio
class TestQueueManager:
    async def test_add_and_next(self) -> None:
        q = QueueManager(guild_id=1)
        t1 = make_track("Track 1")
        t2 = make_track("Track 2")
        await q.add(t1)
        await q.add(t2)

        assert q.size == 2
        nxt = await q.next()
        assert nxt is not None
        assert nxt.title == "Track 1"
        assert q.size == 1
        assert q.current is not None
        assert q.current.title == "Track 1"

    async def test_queue_empty_after_all_played(self) -> None:
        q = QueueManager(guild_id=2)
        await q.add(make_track("A"))
        await q.next()
        nxt = await q.next()
        assert nxt is None
        assert q.is_empty

    async def test_loop_track(self) -> None:
        q = QueueManager(guild_id=3)
        q.loop_mode = LoopMode.TRACK
        t = make_track("Loop Me")
        await q.add(t)
        first = await q.next()
        second = await q.next()
        assert first is not None
        assert second is not None
        assert first.title == second.title

    async def test_loop_queue(self) -> None:
        q = QueueManager(guild_id=4)
        q.loop_mode = LoopMode.QUEUE
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        first = await q.next()
        second = await q.next()
        # After playing A, it should be re-added to queue
        assert first is not None and first.title == "A"
        assert second is not None and second.title == "B"
        assert q.size == 1  # A foi re-adicionado

    async def test_shuffle(self) -> None:
        q = QueueManager(guild_id=5)
        for i in range(10):
            await q.add(make_track(f"Track {i}"))
        original = [t.title for t in q.queue]
        await q.shuffle()
        shuffled = [t.title for t in q.queue]
        # Pode raramente falhar se embaralhar na mesma ordem
        assert set(original) == set(shuffled)

    async def test_remove(self) -> None:
        q = QueueManager(guild_id=6)
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        await q.add(make_track("C"))
        removed = await q.remove(2)
        assert removed is not None and removed.title == "B"
        assert q.size == 2

    async def test_remove_invalid_position(self) -> None:
        q = QueueManager(guild_id=7)
        await q.add(make_track("A"))
        result = await q.remove(5)
        assert result is None

    async def test_move(self) -> None:
        q = QueueManager(guild_id=8)
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        await q.add(make_track("C"))
        ok = await q.move(1, 3)
        assert ok
        titles = [t.title for t in q.queue]
        assert titles == ["B", "C", "A"]

    async def test_max_size(self) -> None:
        q = QueueManager(guild_id=9, max_size=2)
        assert await q.add(make_track("A"))
        assert await q.add(make_track("B"))
        assert not await q.add(make_track("C"))
        assert q.size == 2

    async def test_clear(self) -> None:
        q = QueueManager(guild_id=10)
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        await q.clear()
        assert q.is_empty
        assert q.current is None

    async def test_history(self) -> None:
        q = QueueManager(guild_id=11)
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        await q.next()  # current = A
        await q.next()  # current = B, A in history
        assert len(q.history) == 1
        assert q.history[0].title == "A"

    async def test_previous(self) -> None:
        q = QueueManager(guild_id=12)
        await q.add(make_track("A"))
        await q.add(make_track("B"))
        await q.next()  # current = A
        await q.next()  # current = B, A in history
        prev = await q.previous()
        assert prev is not None and prev.title == "A"

    async def test_to_dicts_and_load(self) -> None:
        q = QueueManager(guild_id=13)
        t = make_track("Serialize Me", "https://example.com/test")
        await q.add(t)
        dicts = q.to_dicts()

        q2 = QueueManager(guild_id=14)
        q2.load_from_dicts(dicts)
        assert q2.size == 1
        assert q2.queue[0].title == "Serialize Me"
