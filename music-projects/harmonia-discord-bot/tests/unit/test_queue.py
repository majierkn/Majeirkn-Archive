from bot.player.queue import MusicQueue
from bot.player.track import Track
def t(i): return Track(str(i),f'T{i}','u')
def test_queue_operations():
 q=MusicQueue(3); q.add(t(1)); q.add(t(2)); assert q.remove(1).title=='T1'; q.add(t(3)); q.move(1,2); assert len(q)==2; q.clear(); assert q.is_empty
