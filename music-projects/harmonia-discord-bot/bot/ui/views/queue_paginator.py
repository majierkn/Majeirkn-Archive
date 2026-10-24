import discord
class QueueView(discord.ui.View):
    def __init__(self, player): super().__init__(timeout=60); self.player=player
