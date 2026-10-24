from __future__ import annotations

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_permissions
from utils.embeds import erro_embed, info_embed, sucesso_embed
from utils.time import parse_duration, human_timedelta


class Sorteios(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _run_giveaway(self, message: discord.Message, winners_count: int) -> list[discord.User]:
        await message.add_reaction("🎉")
        fetched = await message.channel.fetch_message(message.id)
        reaction = discord.utils.get(fetched.reactions, emoji="🎉")
        if not reaction:
            return []
        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            return []
        return random.sample(users, k=min(winners_count, len(users)))

    @app_commands.command(name="sorteio_criar", description="Criar sorteio com duração.")
    @app_commands.guild_only()
    async def sorteio_criar(self, interaction: discord.Interaction, premio: str, duracao: str, ganhadores: app_commands.Range[int, 1, 10] = 1) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        try:
            delta = parse_duration(duracao)
        except ValueError as exc:
            await interaction.response.send_message(embed=erro_embed("Duração inválida", str(exc)), ephemeral=True)
            return
        embed = info_embed("🎉 Sorteio", f"Prêmio: **{premio}**\nGanhadores: `{ganhadores}`\nDuração: `{human_timedelta(delta)}`\nReaja com 🎉 para participar.")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🎉")

        async def finish():
            await asyncio.sleep(delta.total_seconds())
            winners = await self._run_giveaway(msg, ganhadores)
            if winners:
                await msg.reply(embed=sucesso_embed("Sorteio encerrado", f"Prêmio: **{premio}**\nVencedores: {', '.join(w.mention for w in winners)}"))
            else:
                await msg.reply(embed=erro_embed("Sorteio encerrado", "Nenhum participante válido."))
        self.bot.loop.create_task(finish())

    @app_commands.command(name="sorteio_rapido", description="Sortear rapidamente um membro online do servidor.")
    @app_commands.guild_only()
    async def sorteio_rapido(self, interaction: discord.Interaction, premio: str = "Prêmio rápido") -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        members = [m for m in interaction.guild.members if not m.bot]
        if not members:
            await interaction.response.send_message(embed=erro_embed("Sem participantes", "Não encontrei membros válidos."), ephemeral=True)
            return
        winner = random.choice(members)
        await interaction.response.send_message(embed=sucesso_embed("Sorteio rápido", f"Prêmio: **{premio}**\nVencedor: {winner.mention}"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sorteios(bot))
