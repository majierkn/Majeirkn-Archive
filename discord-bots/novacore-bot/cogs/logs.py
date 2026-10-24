from __future__ import annotations

import discord
from discord.ext import commands

from utils.embeds import enviar_log


class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        await enviar_log(
            self.bot,
            message.guild,
            "🗑️ Mensagem apagada",
            f"Autor: {message.author.mention} (`{message.author.id}`)\nCanal: {message.channel.mention}\nConteúdo: `{(message.content or 'Sem texto')[:900]}`",
            0xE74C3C,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        await enviar_log(
            self.bot,
            before.guild,
            "✏️ Mensagem editada",
            f"Autor: {before.author.mention} (`{before.author.id}`)\nCanal: {before.channel.mention}\nAntes: `{(before.content or 'Sem texto')[:700]}`\nDepois: `{(after.content or 'Sem texto')[:700]}`",
            0x3498DB,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await enviar_log(self.bot, member.guild, "📥 Membro entrou", f"Membro: {member.mention} (`{member.id}`)", 0x2ECC71)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await enviar_log(self.bot, member.guild, "📤 Membro saiu", f"Membro: `{member}` (`{member.id}`)", 0xE67E22)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        await enviar_log(self.bot, channel.guild, "➕ Canal criado", f"Canal: `{channel.name}` (`{channel.id}`)", 0x2ECC71)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await enviar_log(self.bot, channel.guild, "➖ Canal apagado", f"Canal: `{channel.name}` (`{channel.id}`)", 0xE74C3C)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logs(bot))
