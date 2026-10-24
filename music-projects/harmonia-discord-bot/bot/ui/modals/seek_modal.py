import discord
class SeekModal(discord.ui.Modal,title='Ir para tempo'):
    time=discord.ui.TextInput(label='Tempo (HH:MM:SS ou segundos)')
    async def on_submit(self,interaction): await interaction.response.send_message('✅ Solicitação recebida.',ephemeral=True)
