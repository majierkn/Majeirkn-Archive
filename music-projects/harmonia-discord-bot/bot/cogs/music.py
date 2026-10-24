import discord
from discord import app_commands
from discord.ext import commands
from bot.resolvers.ytdlp_resolver import YTDLPResolver
from bot.ui.embeds.music_embeds import now_playing
from bot.ui.embeds.error_embeds import error_embed
class MusicCog(commands.Cog):
    def __init__(self,bot): self.bot; self.resolver=YTDLPResolver(bot.settings)
    @app_commands.command(name='play',description='Toca ou enfileira uma música')
    async def play(self,interaction,query:str):
        await interaction.response.defer(); p=self.bot.player_manager.get_or_create(interaction.guild_id)
        try:
            tracks=await self.resolver.resolve(query,interaction.user.id,interaction.user.display_name)
            for t in tracks[:1]: p.queue.add(t)
            await interaction.followup.send(embed=now_playing(tracks[0]))
        except Exception as exc: await interaction.followup.send(embed=error_embed(getattr(exc,'user_message','Não foi possível carregar a música.')))
    @app_commands.command(name='search',description='Busca músicas')
    async def search(self,interaction,query:str): await self.play(interaction,query)
    @app_commands.command(name='nowplaying',description='Mostra a música atual')
    async def nowplaying(self,interaction):
        p=self.bot.player_manager.get(interaction.guild_id); await interaction.response.send_message(embed=now_playing(p.current_track) if p and p.current_track else error_embed('Nada está tocando.'))
    @app_commands.command(name='stop',description='Para e limpa a fila')
    async def stop(self,interaction): p=self.bot.player_manager.get(interaction.guild_id); await p.stop() if p else None; await interaction.response.send_message('⏹️ Reprodução parada e fila limpa.')
    @app_commands.command(name='leave',description='Sai do canal de voz')
    async def leave(self,interaction): await self.bot.player_manager.destroy(interaction.guild_id); await interaction.response.send_message('👋 Saí do canal de voz.')
