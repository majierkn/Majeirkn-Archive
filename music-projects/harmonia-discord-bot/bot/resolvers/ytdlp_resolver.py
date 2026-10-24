import asyncio
import yt_dlp
from bot.player.track import Track
from bot.core.errors import TrackNotFoundError, TrackTooLongError
class YTDLPResolver:
    def __init__(self, settings): self.settings=settings
    async def resolve(self, query, requested_by_id=None, requested_by_name=None):
        opts={'format':'bestaudio/best','quiet':True,'no_warnings':True,'default_search':'ytsearch5','noplaylist':False}
        if self.settings.ytdlp_cookiefile: opts['cookiefile']=self.settings.ytdlp_cookiefile
        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(query if '://' in query else 'ytsearch5:'+query, download=False)
        try: info=await asyncio.to_thread(extract)
        except Exception as exc: raise TrackNotFoundError() from exc
        entries=info.get('entries') or [info]; tracks=[]
        for entry in entries:
            if not entry: continue
            t=Track.from_ytdlp_info(entry, requested_by_id, requested_by_name)
            if t.duration>36000: raise TrackTooLongError()
            tracks.append(t)
        if not tracks: raise TrackNotFoundError()
        return tracks
    async def resolve_stream_url(self, webpage_url):
        def extract():
            with yt_dlp.YoutubeDL({'format':'bestaudio/best','quiet':True}) as ydl: return ydl.extract_info(webpage_url,download=False).get('url')
        return await asyncio.to_thread(extract)
