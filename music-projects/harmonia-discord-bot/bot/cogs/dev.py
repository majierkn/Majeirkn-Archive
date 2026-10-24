from discord.ext import commands
class DevCog(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.command(name='sync')
    @commands.is_owner()
    async def sync(self,ctx): await self.bot.tree.sync(); await ctx.send('Comandos sincronizados.')
    @commands.command(name='reload')
    @commands.is_owner()
    async def reload(self,ctx,cog:str): await self.bot.reload_extension('bot.cogs.'+cog); await ctx.send('Cog recarregado.')
