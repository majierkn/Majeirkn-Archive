from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import info_embed

CATEGORIAS = {
    "🛡️ Moderação": "/banir, /desbanir, /expulsar, /castigar, /remover_castigo, /avisar, /avisos, /remover_aviso, /limpar, /trancar, /destrancar, /modo_lento, /nick, /cargo_adicionar, /cargo_remover, /anunciar, /falar",
    "⚙️ Configuração": "/config_logs, /config_boasvindas, /config_saida, /config_autocargo, /config_ticket, /config_automod, /config_xp, /config_economia, /config_ver",
    "🎫 Tickets": "/painel_ticket, /fechar_ticket, /adicionar_ticket, /remover_ticket, /renomear_ticket",
    "📈 Níveis": "/rank, /ranking, /xp_adicionar, /xp_remover, /nivel_definir, /recompensa_nivel, /recompensas",
    "💰 Economia": "/saldo, /daily, /trabalhar, /apostar, /transferir, /loja, /loja_adicionar, /loja_remover, /comprar, /inventario, /ranking_moedas, /moedas_adicionar, /moedas_remover",
    "🧰 Utilidade": "/ping, /usuario, /servidor, /avatar, /banner, /botinfo, /canal, /cargo, /emoji, /convite, /calcular, /enquete, /lembrete",
    "🎲 Diversão": "/dado, /moeda, /bola8, /escolher, /ship, /abracar, /tapa, /beijar, /piada, /meme_texto, /ascii, /ppt",
    "🎉 Sorteios": "/sorteio_criar, /sorteio_rapido",
    "🎵 Música": "/entrar_voz, /sair_voz, /tocar, /pausar_musica, /continuar_musica, /parar_musica, /pular_musica, /fila_musica, /volume_musica",
}


class Ajuda(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ajuda", description="Abrir menu de ajuda do NovaCore Bot.")
    async def ajuda(self, interaction: discord.Interaction) -> None:
        embed = info_embed("Ajuda — NovaCore Bot", "Comandos separados por categoria. Todos usam slash commands em português.")
        for name, value in CATEGORIAS.items():
            embed.add_field(name=name, value=value[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="comandos", description="Listar todos os comandos do bot.")
    async def comandos(self, interaction: discord.Interaction) -> None:
        total = sum(len(v.split(",")) for v in CATEGORIAS.values())
        embed = info_embed("Comandos", f"Total aproximado: **{total} comandos**.")
        for name, value in CATEGORIAS.items():
            embed.add_field(name=name, value=value[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ajuda(bot))
