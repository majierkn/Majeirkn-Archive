import discord
class SearchView(discord.ui.View):
    def __init__(self, tracks, callback): super().__init__(timeout=30); self.tracks,self.callback=tracks,callback
    async def on_timeout(self):
        for child in self.children: child.disabled=True
