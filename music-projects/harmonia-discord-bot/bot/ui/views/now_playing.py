import discord
class NowPlayingView(discord.ui.View):
    def __init__(self, manager): super().__init__(timeout=None); self.manager=manager
    @discord.ui.button(label='⏭️ Pular',style=discord.ButtonStyle.secondary,custom_id='np_skip')
    async def skip(self, interaction, button):
        p=self.manager.get(interaction.guild_id); await p.skip() if p else None; await interaction.response.send_message('⏭️ Faixa pulada.',ephemeral=True)
