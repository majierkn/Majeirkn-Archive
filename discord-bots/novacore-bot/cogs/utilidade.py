from __future__ import annotations

import ast
import asyncio
import operator as op
import re
import platform
from typing import Optional
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import erro_embed, info_embed, sucesso_embed
from utils.time import parse_duration, human_timedelta

ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}


def safe_eval(expr: str) -> float:
    def eval_node(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPS:
            return ALLOWED_OPS[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPS:
            return ALLOWED_OPS[type(node.op)](eval_node(node.operand))
        raise ValueError("Expressão inválida.")
    parsed = ast.parse(expr, mode="eval")
    return eval_node(parsed.body)


class Utilidade(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Ver latência do bot.")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=info_embed("Pong", f"Latência: `{round(self.bot.latency * 1000)}ms`."))

    @app_commands.command(name="usuario", description="Ver informações de um usuário.")
    @app_commands.guild_only()
    async def usuario(self, interaction: discord.Interaction, membro: Optional[discord.Member] = None) -> None:
        membro = membro or interaction.user
        embed = info_embed("Usuário", f"Menção: {membro.mention}\nID: `{membro.id}`\nConta criada: <t:{int(membro.created_at.timestamp())}:F>\nEntrou: <t:{int(membro.joined_at.timestamp()) if membro.joined_at else 0}:F>")
        embed.set_thumbnail(url=membro.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="servidor", description="Ver informações do servidor.")
    @app_commands.guild_only()
    async def servidor(self, interaction: discord.Interaction) -> None:
        g = interaction.guild
        embed = info_embed("Servidor", f"Nome: **{g.name}**\nID: `{g.id}`\nMembros: `{g.member_count}`\nCanais: `{len(g.channels)}`\nCargos: `{len(g.roles)}`\nCriado em: <t:{int(g.created_at.timestamp())}:F>")
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Ver avatar de um usuário.")
    async def avatar(self, interaction: discord.Interaction, usuario: Optional[discord.User] = None) -> None:
        usuario = usuario or interaction.user
        embed = info_embed("Avatar", f"Avatar de {usuario.mention}")
        embed.set_image(url=usuario.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="banner", description="Ver banner de um usuário.")
    async def banner(self, interaction: discord.Interaction, usuario: Optional[discord.User] = None) -> None:
        usuario = usuario or interaction.user
        fetched = await self.bot.fetch_user(usuario.id)
        if not fetched.banner:
            await interaction.response.send_message(embed=erro_embed("Sem banner", "Esse usuário não possui banner visível."), ephemeral=True)
            return
        embed = info_embed("Banner", f"Banner de {usuario.mention}")
        embed.set_image(url=fetched.banner.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Ver informações do bot.")
    async def botinfo(self, interaction: discord.Interaction) -> None:
        embed = info_embed("NovaCore Bot", f"Python: `{platform.python_version()}`\ndiscord.py: `{discord.__version__}`\nServidores: `{len(self.bot.guilds)}`\nComandos: `{len(self.bot.tree.get_commands())}`")
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="canal", description="Ver informações de um canal.")
    @app_commands.guild_only()
    async def canal(self, interaction: discord.Interaction, canal: Optional[discord.TextChannel] = None) -> None:
        canal = canal or interaction.channel
        await interaction.response.send_message(embed=info_embed("Canal", f"Nome: {canal.mention}\nID: `{canal.id}`\nCriado: <t:{int(canal.created_at.timestamp())}:F>"))

    @app_commands.command(name="cargo", description="Ver informações de um cargo.")
    @app_commands.guild_only()
    async def cargo(self, interaction: discord.Interaction, cargo: discord.Role) -> None:
        await interaction.response.send_message(embed=info_embed("Cargo", f"Cargo: {cargo.mention}\nID: `{cargo.id}`\nMembros: `{len(cargo.members)}`\nCriado: <t:{int(cargo.created_at.timestamp())}:F>"))

    @app_commands.command(name="emoji", description="Ver informações de um emoji customizado.")
    @app_commands.guild_only()
    async def emoji(self, interaction: discord.Interaction, emoji: str) -> None:
        # discord.py app_commands não aceita discord.Emoji como anotação direta.
        # Por isso recebemos texto e resolvemos o emoji manualmente por menção, ID ou nome.
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(embed=erro_embed("Servidor inválido", "Use este comando dentro de um servidor."), ephemeral=True)
            return

        emoji_id = None
        match = re.fullmatch(r"<a?:([a-zA-Z0-9_]+):(\d+)>", emoji.strip())
        if match:
            emoji_id = int(match.group(2))
        elif emoji.strip().isdigit():
            emoji_id = int(emoji.strip())

        custom_emoji = None
        if emoji_id is not None:
            custom_emoji = discord.utils.get(guild.emojis, id=emoji_id)
        else:
            nome = emoji.strip().strip(":")
            custom_emoji = discord.utils.get(guild.emojis, name=nome)

        if custom_emoji is None:
            await interaction.response.send_message(
                embed=erro_embed("Emoji não encontrado", "Envie um emoji customizado do servidor, o ID ou o nome dele."),
                ephemeral=True,
            )
            return

        embed = info_embed("Emoji", f"Nome: `{custom_emoji.name}`\nID: `{custom_emoji.id}`\nAnimado: `{custom_emoji.animated}`")
        embed.set_thumbnail(url=custom_emoji.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="convite", description="Criar convite do canal atual.")
    @app_commands.guild_only()
    async def convite(self, interaction: discord.Interaction) -> None:
        invite = await interaction.channel.create_invite(max_age=3600, max_uses=5, reason=f"Convite criado por {interaction.user}")
        await interaction.response.send_message(embed=sucesso_embed("Convite criado", f"{invite.url}\nExpira em 1 hora e permite 5 usos."), ephemeral=True)

    @app_commands.command(name="calcular", description="Calcular uma expressão matemática simples.")
    async def calcular(self, interaction: discord.Interaction, expressao: str) -> None:
        try:
            result = safe_eval(expressao.replace(",", "."))
        except Exception:
            await interaction.response.send_message(embed=erro_embed("Expressão inválida", "Use apenas números e operadores: + - * / // % **."), ephemeral=True)
            return
        await interaction.response.send_message(embed=info_embed("Resultado", f"`{expressao}` = **{result}**"))

    @app_commands.command(name="enquete", description="Criar enquete simples com reações.")
    @app_commands.guild_only()
    async def enquete(self, interaction: discord.Interaction, pergunta: str) -> None:
        embed = info_embed("Enquete", pergunta[:3000])
        embed.add_field(name="Como votar", value="👍 Sim\n👎 Não", inline=False)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @app_commands.command(name="lembrete", description="Criar lembrete simples.")
    async def lembrete(self, interaction: discord.Interaction, duracao: str, texto: str) -> None:
        try:
            delta = parse_duration(duracao)
        except ValueError as exc:
            await interaction.response.send_message(embed=erro_embed("Duração inválida", str(exc)), ephemeral=True)
            return
        await interaction.response.send_message(embed=sucesso_embed("Lembrete criado", f"Vou lembrar você em `{human_timedelta(delta)}`."), ephemeral=True)
        async def wait_and_send():
            await asyncio.sleep(delta.total_seconds())
            try:
                await interaction.user.send(embed=info_embed("Lembrete", texto[:1900]))
            except discord.HTTPException:
                pass
        self.bot.loop.create_task(wait_and_send())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utilidade(bot))
