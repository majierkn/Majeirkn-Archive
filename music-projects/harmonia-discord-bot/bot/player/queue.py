import random
from bot.core.errors import QueueFullError
class MusicQueue:
    def __init__(self,maxsize=500): self.maxsize=maxsize; self._items=[]
    def add(self, track):
        if len(self._items)>=self.maxsize: raise QueueFullError()
        self._items.append(track)
    def remove(self, position): return self._items.pop(position-1)
    def clear(self): self._items.clear()
    def shuffle(self): random.shuffle(self._items)
    def move(self, source, target): self._items.insert(target-1,self._items.pop(source-1))
    def peek(self): return self._items[0] if self._items else None
    def drain(self): items=self._items[:]; self.clear(); return items
    def __len__(self): return len(self._items)
    def __iter__(self): return iter(self._items)
    @property
    def is_empty(self): return not self._items
    def page_count(self, per_page=10): return max(1,(len(self._items)+per_page-1)//per_page)
