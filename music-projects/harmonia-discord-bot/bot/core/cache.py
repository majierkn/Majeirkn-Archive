import time
from collections import OrderedDict
class TTLCache:
    def __init__(self, maxsize=1000, ttl=3600): self.maxsize, self.ttl, self._data = maxsize, ttl, OrderedDict()
    def get(self, key):
        item = self._data.get(key)
        if not item: return None
        if time.monotonic() - item[0] >= self.ttl: self._data.pop(key, None); return None
        self._data.move_to_end(key); return item[1]
    def set(self, key, value):
        self._data[key] = (time.monotonic(), value); self._data.move_to_end(key)
        while len(self._data) > self.maxsize: self._data.popitem(last=False)
    def clear(self): self._data.clear()
    def __len__(self): return len(self._data)
