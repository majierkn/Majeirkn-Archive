import discord
from discord import app_commands
from discord.ext import commands
class PlaylistCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    group=app_commands.Group(name='playlist',description='Gerencie playlists')
    @group.command(name='criar',description='Cria uma playlist')
    async def criar(self,interaction,nome:str,descricao:str=''): await self.bot.db.create_playlist(interaction.user.id,interaction.guild_id,nome,descricao); await interaction.response.send_message(f'✅ Playlist **{nome}** criada.')
    @group.command(name='listar',description='Lista suas playlists')
    async def listar(self,interaction): rows=await self.bot.db.list_playlists(interaction.user.id,interaction.guild_id); await interaction.response.send_message('📚 '+(', '.join(r['name'] for r in rows) or 'Nenhuma playlist criada.'))
