from __future__ import annotations

import re

import discord
from discord.ext import commands

from utils.embeds import enviar_log

LINK_RE = re.compile(r"https?://|discord\.gg/|www\.", re.IGNORECASE)


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        if not await self.bot.db.get_setting(message.guild.id, "automod.enabled", False):
            return
        member = message.author if isinstance(message.author, discord.Member) else None
        if member and member.guild_permissions.manage_messages:
            return

        reason = None
        content = message.content or ""

        if await self.bot.db.get_setting(message.guild.id, "automod.block_links", True) and LINK_RE.search(content):
            reason = "Envio de link bloqueado"

        bad_words = await self.bot.db.get_setting(message.guild.id, "automod.bad_words", [])
        lowered = content.lower()
        if not reason and any(word in lowered for word in bad_words):
            reason = "Palavra proibida detectada"

        caps_percent = int(await self.bot.db.get_setting(message.guild.id, "automod.caps_percent", 75))
        letters = [c for c in content if c.isalpha()]
        if not reason and len(letters) >= 12:
            upper = sum(1 for c in letters if c.isupper())
            if (upper / len(letters)) * 100 >= caps_percent:
                reason = "Excesso de letras maiúsculas"

        if not reason:
            return

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            await message.channel.send(f"{message.author.mention}, mensagem removida pelo AutoMod: **{reason}**.", delete_after=8)
        except discord.HTTPException:
            pass

        await enviar_log(
            self.bot,
            message.guild,
            "🛡️ AutoMod",
            f"Usuário: {message.author.mention} (`{message.author.id}`)\nCanal: {message.channel.mention}\nMotivo: {reason}\nConteúdo: `{content[:900]}`",
            0xE67E22,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
