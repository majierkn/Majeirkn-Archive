import discord
from discord import app_commands
from discord.ext import commands
from bot.ui.embeds.music_embeds import queue_embed
class QueueCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='queue',description='Exibe a fila')
    async def queue(self,interaction,pagina:int=1): p=self.bot.player_manager.get(interaction.guild_id); await interaction.response.send_message(embed=queue_embed(p) if p else discord.Embed(description='A fila está vazia.'))
    @app_commands.command(name='skip',description='Pula a faixa atual')
    async def skip(self,interaction,quantidade:int=1): p=self.bot.player_manager.get(interaction.guild_id); [await p.skip() for _ in range(max(1,quantidade))] if p else None; await interaction.response.send_message('⏭️ Faixa pulada.')
    @app_commands.command(name='clear',description='Limpa a fila')
    async def clear(self,interaction): p=self.bot.player_manager.get(interaction.guild_id); p.queue.clear() if p else None; await interaction.response.send_message('🧹 Fila limpa.')
    @app_commands.command(name='shuffle',description='Embaralha a fila')
    async def shuffle(self,interaction): p=self.bot.player_manager.get(interaction.guild_id); p.queue.shuffle() if p else None; await interaction.response.send_message('🔀 Fila embaralhada.')
    @app_commands.command(name='remove',description='Remove uma posição')
    async def remove(self,interaction,posicao:int): p=self.bot.player_manager.get(interaction.guild_id); p.queue.remove(posicao) if p else None; await interaction.response.send_message('🗑️ Faixa removida.')
    @app_commands.command(name='move',description='Move uma faixa')
    async def move(self,interaction,de:int,para:int): p=self.bot.player_manager.get(interaction.guild_id); p.queue.move(de,para) if p else None; await interaction.response.send_message('↔️ Faixa movida.')
