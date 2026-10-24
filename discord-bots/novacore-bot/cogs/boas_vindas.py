from __future__ import annotations

import discord
from discord.ext import commands

from utils.embeds import base_embed


class BoasVindas(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _format(self, template: str, member: discord.Member) -> str:
        return template.replace("{user}", member.mention).replace("{server}", member.guild.name).replace("{count}", str(member.guild.member_count or 0))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role_id = await self.bot.db.get_setting(member.guild.id, "autorole.role_id")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role and member.guild.me and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Auto cargo NovaCore")
                except discord.HTTPException:
                    pass

        channel_id = await self.bot.db.get_setting(member.guild.id, "welcome.canal_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return
        msg = await self.bot.db.get_setting(member.guild.id, "welcome.mensagem", "Bem-vindo(a), {user}, ao {server}!")
        embed = base_embed("👋 Bem-vindo(a)!", self._format(msg, member), 0x2ECC71)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel_id = await self.bot.db.get_setting(member.guild.id, "leave.canal_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return
        msg = await self.bot.db.get_setting(member.guild.id, "leave.mensagem", "{user} saiu do servidor.")
        embed = base_embed("👋 Saída", self._format(msg, member), 0xE67E22)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BoasVindas(bot))
