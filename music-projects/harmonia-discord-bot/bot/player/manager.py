from bot.player.guild_player import GuildPlayer
class PlayerManager:
    def __init__(self, bot): self.bot = bot; self._players={}
    def get(self,guild_id): return self._players.get(guild_id)
    def get_or_create(self,guild_id):
        if guild_id not in self._players: self._players[guild_id]=GuildPlayer(self.bot,guild_id)
        return self._players[guild_id]
    async def destroy(self,guild_id):
        p=self._players.pop(guild_id,None)
        if p: await p.disconnect()
