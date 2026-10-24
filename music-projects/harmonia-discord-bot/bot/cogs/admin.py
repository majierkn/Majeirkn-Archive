import discord
from discord import app_commands
from discord.ext import commands
class AdminCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='setup',description='Configura o bot neste servidor')
    @app_commands.default_permissions(manage_guild=True)
    async def setup(self,interaction): await self.bot.db.ensure_guild(interaction.guild_id,interaction.guild.name); await interaction.response.send_message('✅ HarmonIA configurado neste servidor.')
    @app_commands.command(name='stats',description='Mostra estatísticas')
    async def stats(self,interaction): await interaction.response.send_message(f'📊 Servidores: **{len(self.bot.guilds)}** | Players ativos: **{len(self.bot.player_manager._players)}**')
