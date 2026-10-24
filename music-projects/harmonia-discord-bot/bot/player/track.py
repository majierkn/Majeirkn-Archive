from dataclasses import dataclass, field
import time
@dataclass(frozen=True, slots=True)
class Track:
    webpage_url: str; title: str; uploader: str; duration: int = 0; thumbnail: str|None = None; source_type: str = "unknown"
    playlist_title: str|None = None; playlist_index: int|None = None; requested_by_id: int|None = None; requested_by_name: str|None = None; requested_at: float = field(default_factory=time.time); stream_url: str|None = None
    @classmethod
    def from_ytdlp_info(cls, info, requested_by_id=None, requested_by_name=None, **kwargs):
        return cls(info.get('webpage_url') or info.get('url'), info.get('title','Sem título'), info.get('uploader') or info.get('channel') or 'Desconhecido', int(info.get('duration') or 0), info.get('thumbnail'), (info.get('extractor_key') or 'unknown').lower(), requested_by_id=requested_by_id, requested_by_name=requested_by_name, stream_url=info.get('url'), **kwargs)
    @property
    def is_live(self): return self.duration == 0
    @property
    def duration_formatted(self):
        if self.is_live: return 'AO VIVO'
        h, r = divmod(self.duration,3600); m,s=divmod(r,60); return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'
