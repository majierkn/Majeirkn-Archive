import discord
from discord.ext import commands
from bot.core.config import get_settings
from bot.core.database import Database
from bot.player.manager import PlayerManager
COGS=['music','queue','controls','playlist','admin','dev']
class HarmonIA(commands.AutoShardedBot):
    def __init__(self):
        s=get_settings(); intents=discord.Intents.default(); intents.voice_states=True; super().__init__(command_prefix=s.bot_prefix,intents=intents,shard_count=s.shard_count,help_command=None); self.settings=s; self.db=Database(s.database_path); self.player_manager=PlayerManager(self)
    async def setup_hook(self):
        await self.db.initialize()
        for cog in COGS: await self.load_extension('bot.cogs.'+cog)
        self.add_view(__import__('bot.ui.views.now_playing',fromlist=['NowPlayingView']).NowPlayingView(self.player_manager))
        if self.settings.sync_commands_on_startup: await self.tree.sync()
    async def on_ready(self): await self.change_presence(activity=discord.Game(self.settings.bot_status))
    async def close(self): await self.db.close(); await super().close()
def create_bot(): return HarmonIA()
