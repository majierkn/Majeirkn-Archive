import discord
from discord import app_commands
from discord.ext import commands
from bot.player.filters import FILTERS
class ControlsCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='volume',description='Define o volume de 0 a 200')
    async def volume(self,interaction,valor:app_commands.Range[int,0,200]|None=None):
        p=self.bot.player_manager.get_or_create(interaction.guild_id)
        if valor is not None:p.volume=valor
        await interaction.response.send_message(f'🔊 Volume: **{p.volume}%**')
    @app_commands.command(name='loop',description='Define o modo de repetição')
    @app_commands.choices(modo=[app_commands.Choice(name=x,value=x) for x in ['none','track','queue']])
    async def loop(self,interaction,modo:app_commands.Choice[str]): p=self.bot.player_manager.get_or_create(interaction.guild_id); p.loop_mode=modo.value; await interaction.response.send_message(f'🔁 Loop: **{modo.value}**')
    @app_commands.command(name='filter',description='Aplica um filtro de áudio')
    @app_commands.choices(filtro=[app_commands.Choice(name=x,value=x) for x in FILTERS])
    async def filter(self,interaction,filtro:app_commands.Choice[str]): p=self.bot.player_manager.get_or_create(interaction.guild_id); p.filter_name=filtro.value; await interaction.response.send_message(f'🎛️ Filtro aplicado: **{filtro.value}**')
