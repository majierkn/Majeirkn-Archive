from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import info_embed


class Diversao(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="dado", description="Rolar um dado.")
    async def dado(self, interaction: discord.Interaction, lados: app_commands.Range[int, 2, 100] = 6) -> None:
        await interaction.response.send_message(embed=info_embed("Dado", f"🎲 Resultado: **{random.randint(1, lados)}** de {lados}."))

    @app_commands.command(name="moeda", description="Jogar cara ou coroa.")
    async def moeda(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=info_embed("Moeda", f"🪙 Caiu **{random.choice(['cara', 'coroa'])}**."))

    @app_commands.command(name="bola8", description="Perguntar algo para a bola 8.")
    async def bola8(self, interaction: discord.Interaction, pergunta: str) -> None:
        respostas = ["Sim.", "Não.", "Talvez.", "Com certeza.", "Melhor não contar com isso.", "Pergunte novamente depois."]
        await interaction.response.send_message(embed=info_embed("Bola 8", f"Pergunta: {pergunta}\nResposta: **{random.choice(respostas)}**"))

    @app_commands.command(name="escolher", description="Escolher entre opções separadas por vírgula.")
    async def escolher(self, interaction: discord.Interaction, opcoes: str) -> None:
        items = [x.strip() for x in opcoes.split(",") if x.strip()]
        if len(items) < 2:
            await interaction.response.send_message("Informe pelo menos duas opções separadas por vírgula.", ephemeral=True)
            return
        await interaction.response.send_message(embed=info_embed("Escolha", f"Eu escolho: **{random.choice(items)}**"))

    @app_commands.command(name="ship", description="Calcular compatibilidade entre duas pessoas.")
    async def ship(self, interaction: discord.Interaction, pessoa1: discord.Member, pessoa2: discord.Member) -> None:
        score = random.randint(0, 100)
        await interaction.response.send_message(embed=info_embed("Ship", f"{pessoa1.mention} + {pessoa2.mention} = **{score}%** de compatibilidade."))

    @app_commands.command(name="abracar", description="Abraçar alguém.")
    async def abracar(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        await interaction.response.send_message(embed=info_embed("Abraço", f"🤗 {interaction.user.mention} abraçou {membro.mention}."))

    @app_commands.command(name="tapa", description="Dar um tapa fictício em alguém.")
    async def tapa(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        await interaction.response.send_message(embed=info_embed("Tapa", f"👋 {interaction.user.mention} deu um tapa fictício em {membro.mention}."))

    @app_commands.command(name="beijar", description="Enviar beijo para alguém.")
    async def beijar(self, interaction: discord.Interaction, membro: discord.Member) -> None:
        await interaction.response.send_message(embed=info_embed("Beijo", f"💋 {interaction.user.mention} mandou um beijo para {membro.mention}."))

    @app_commands.command(name="piada", description="Receber uma piada curta.")
    async def piada(self, interaction: discord.Interaction) -> None:
        piadas = [
            "Por que o computador foi ao médico? Porque estava com vírus.",
            "O que o zero disse para o oito? Belo cinto!",
            "Qual é o café mais perigoso? O ex-presso.",
        ]
        await interaction.response.send_message(embed=info_embed("Piada", random.choice(piadas)))

    @app_commands.command(name="meme_texto", description="Criar meme em texto.")
    async def meme_texto(self, interaction: discord.Interaction, texto: str) -> None:
        await interaction.response.send_message(f"```\n{texto.upper()[:1800]}\n```")

    @app_commands.command(name="ascii", description="Criar texto ASCII simples.")
    async def ascii(self, interaction: discord.Interaction, texto: str) -> None:
        safe = texto[:20]
        border = "=" * (len(safe) + 8)
        await interaction.response.send_message(f"```\n{border}\n=== {safe} ===\n{border}\n```")

    @app_commands.command(name="ppt", description="Jogar pedra, papel e tesoura.")
    @app_commands.choices(escolha=[
        app_commands.Choice(name="pedra", value="pedra"),
        app_commands.Choice(name="papel", value="papel"),
        app_commands.Choice(name="tesoura", value="tesoura"),
    ])
    async def ppt(self, interaction: discord.Interaction, escolha: app_commands.Choice[str]) -> None:
        bot = random.choice(["pedra", "papel", "tesoura"])
        user = escolha.value
        if bot == user:
            result = "Empate."
        elif (user, bot) in [("pedra", "tesoura"), ("papel", "pedra"), ("tesoura", "papel")]:
            result = "Você ganhou."
        else:
            result = "Eu ganhei."
        await interaction.response.send_message(embed=info_embed("Pedra, papel e tesoura", f"Você: **{user}**\nBot: **{bot}**\nResultado: **{result}**"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Diversao(bot))
