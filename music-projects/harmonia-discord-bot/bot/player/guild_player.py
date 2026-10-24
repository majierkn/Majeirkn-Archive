import discord
from bot.player.queue import MusicQueue
class GuildPlayer:
    def __init__(self, bot, guild_id): self.bot,self.guild_id=bot,guild_id; self.queue=MusicQueue(bot.settings.max_queue_size); self.voice_client=None; self.current_track=None; self.volume=bot.settings.default_volume; self.loop_mode='none'; self.filter_name=None
    async def connect(self, channel):
        if self.voice_client and self.voice_client.is_connected(): return self.voice_client
        self.voice_client=await channel.connect(); return self.voice_client
    async def disconnect(self):
        if self.voice_client: await self.voice_client.disconnect(force=True)
        self.voice_client=None; self.current_track=None
    async def stop(self):
        self.queue.clear(); self.current_track=None
        if self.voice_client and self.voice_client.is_playing(): self.voice_client.stop()
    async def skip(self):
        if self.voice_client and self.voice_client.is_playing(): self.voice_client.stop(); return True
        return False
    @property
    def is_playing(self): return bool(self.voice_client and self.voice_client.is_playing())
