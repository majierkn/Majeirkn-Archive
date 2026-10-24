from __future__ import annotations

import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_permissions, validate_role_management
from utils.embeds import info_embed, sucesso_embed


class Niveis(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        if not await self.bot.db.get_setting(message.guild.id, "xp.enabled", True):
            return
        cooldown = int(await self.bot.db.get_setting(message.guild.id, "xp.cooldown", 60))
        xp_min = int(await self.bot.db.get_setting(message.guild.id, "xp.min", 15))
        xp_max = int(await self.bot.db.get_setting(message.guild.id, "xp.max", 30))
        amount = random.randint(xp_min, xp_max)
        xp, level, up = await self.bot.db.add_xp(message.guild.id, message.author.id, amount, cooldown)
        if not up:
            return
        role_id = await self.bot.db.get_level_reward(message.guild.id, level)
        if role_id and isinstance(message.author, discord.Member):
            role = message.guild.get_role(role_id)
            if role and message.guild.me and role < message.guild.me.top_role:
                try:
                    await message.author.add_roles(role, reason=f"Recompensa de nível {level}")
                except discord.HTTPException:
                    pass
        try:
            await message.channel.send(f"🎉 {message.author.mention} subiu para o nível **{level}**!", delete_after=12)
        except discord.HTTPException:
            pass

    @app_commands.command(name="rank", description="Ver rank de XP de um usuário.")
    @app_commands.guild_only()
    async def rank(self, interaction: discord.Interaction, membro: Optional[discord.Member] = None) -> None:
        membro = membro or interaction.user
        row = await self.bot.db.get_rank(interaction.guild_id, membro.id)
        xp = int(row["xp"]) if row else 0
        nivel = int(row["nivel"]) if row else 0
        embed = info_embed("Rank", f"Usuário: {membro.mention}\nNível: **{nivel}**\nXP: **{xp}**")
        embed.set_thumbnail(url=membro.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ranking", description="Ver ranking de XP do servidor.")
    @app_commands.guild_only()
    async def ranking(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.get_leaderboard_xp(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message(embed=info_embed("Ranking", "Ainda não há XP registrado."))
            return
        lines = []
        for i, row in enumerate(rows, 1):
            user = interaction.guild.get_member(row["user_id"])
            name = user.mention if user else f"`{row['user_id']}`"
            lines.append(f"**{i}.** {name} — nível `{row['nivel']}` • `{row['xp']}` XP")
        await interaction.response.send_message(embed=info_embed("Ranking de XP", "\n".join(lines)))

    @app_commands.command(name="xp_adicionar", description="Adicionar XP a um usuário.")
    @app_commands.guild_only()
    async def xp_adicionar(self, interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100000]) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        xp, level = await self.bot.db.change_xp(interaction.guild_id, membro.id, quantidade)
        await interaction.response.send_message(embed=sucesso_embed("XP adicionado", f"{membro.mention}: `{xp}` XP, nível `{level}`."), ephemeral=True)

    @app_commands.command(name="xp_remover", description="Remover XP de um usuário.")
    @app_commands.guild_only()
    async def xp_remover(self, interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100000]) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        xp, level = await self.bot.db.change_xp(interaction.guild_id, membro.id, -quantidade)
        await interaction.response.send_message(embed=sucesso_embed("XP removido", f"{membro.mention}: `{xp}` XP, nível `{level}`."), ephemeral=True)

    @app_commands.command(name="nivel_definir", description="Definir nível de um usuário.")
    @app_commands.guild_only()
    async def nivel_definir(self, interaction: discord.Interaction, membro: discord.Member, nivel: app_commands.Range[int, 0, 1000]) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        xp, level = await self.bot.db.set_level(interaction.guild_id, membro.id, nivel)
        await interaction.response.send_message(embed=sucesso_embed("Nível definido", f"{membro.mention}: nível `{level}`, XP `{xp}`."), ephemeral=True)

    @app_commands.command(name="recompensa_nivel", description="Definir cargo de recompensa por nível.")
    @app_commands.guild_only()
    async def recompensa_nivel(self, interaction: discord.Interaction, nivel: app_commands.Range[int, 1, 1000], cargo: discord.Role) -> None:
        if not await require_permissions(interaction, manage_roles=True): return
        if not await validate_role_management(interaction, cargo): return
        await self.bot.db.set_level_reward(interaction.guild_id, nivel, cargo.id)
        await interaction.response.send_message(embed=sucesso_embed("Recompensa configurada", f"Nível `{nivel}` dará o cargo {cargo.mention}."), ephemeral=True)

    @app_commands.command(name="recompensas", description="Listar recompensas de nível.")
    @app_commands.guild_only()
    async def recompensas(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.list_level_rewards(interaction.guild_id)
        if not rows:
            await interaction.response.send_message(embed=info_embed("Recompensas", "Nenhuma recompensa configurada."))
            return
        lines = []
        for row in rows:
            role = interaction.guild.get_role(row["role_id"])
            lines.append(f"Nível `{row['nivel']}` → {role.mention if role else row['role_id']}")
        await interaction.response.send_message(embed=info_embed("Recompensas de nível", "\n".join(lines)))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Niveis(bot))
