import discord
class PlaylistCreateModal(discord.ui.Modal,title='Criar playlist'):
    name=discord.ui.TextInput(label='Nome',max_length=50)
    description=discord.ui.TextInput(label='Descrição',style=discord.TextStyle.paragraph,required=False,max_length=200)
    async def on_submit(self,interaction): await interaction.response.send_message('✅ Playlist criada.',ephemeral=True)
