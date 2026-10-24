from __future__ import annotations

import random
from typing import Optional
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import require_permissions, validate_role_management
from utils.embeds import erro_embed, info_embed, sucesso_embed


class Economia(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def currency(self, guild_id: int) -> str:
        return await self.bot.db.get_setting(guild_id, "economy.currency", "moedas")

    @app_commands.command(name="saldo", description="Ver saldo de moedas.")
    @app_commands.guild_only()
    async def saldo(self, interaction: discord.Interaction, membro: Optional[discord.Member] = None) -> None:
        membro = membro or interaction.user
        bal = await self.bot.db.get_balance(interaction.guild_id, membro.id)
        await interaction.response.send_message(embed=info_embed("Saldo", f"{membro.mention} possui **{bal} {await self.currency(interaction.guild_id)}**."))

    @app_commands.command(name="daily", description="Coletar recompensa diária.")
    @app_commands.guild_only()
    async def daily(self, interaction: discord.Interaction) -> None:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        ok = await self.bot.db.mark_daily(interaction.guild_id, interaction.user.id, today)
        if not ok:
            await interaction.response.send_message(embed=erro_embed("Daily já coletado", "Você já pegou sua recompensa diária hoje."), ephemeral=True)
            return
        amount = int(await self.bot.db.get_setting(interaction.guild_id, "economy.daily", 500))
        bal = await self.bot.db.change_balance(interaction.guild_id, interaction.user.id, amount)
        await interaction.response.send_message(embed=sucesso_embed("Daily coletado", f"Você recebeu **{amount} {await self.currency(interaction.guild_id)}**. Saldo: `{bal}`."))

    @app_commands.command(name="trabalhar", description="Trabalhar para ganhar moedas.")
    @app_commands.guild_only()
    async def trabalhar(self, interaction: discord.Interaction) -> None:
        ok = await self.bot.db.can_work(interaction.guild_id, interaction.user.id)
        if not ok:
            await interaction.response.send_message(embed=erro_embed("Aguarde", "Você só pode trabalhar uma vez por hora."), ephemeral=True)
            return
        amount = random.randint(80, 300)
        bal = await self.bot.db.change_balance(interaction.guild_id, interaction.user.id, amount)
        jobs = ["programou um bot", "organizou a comunidade", "fez uma entrega", "ajudou no suporte", "minerou dados"]
        await interaction.response.send_message(embed=sucesso_embed("Trabalho concluído", f"Você {random.choice(jobs)} e ganhou **{amount} {await self.currency(interaction.guild_id)}**. Saldo: `{bal}`."))

    @app_commands.command(name="apostar", description="Apostar moedas em cara ou coroa.")
    @app_commands.guild_only()
    async def apostar(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100000]) -> None:
        bal = await self.bot.db.get_balance(interaction.guild_id, interaction.user.id)
        if bal < quantidade:
            await interaction.response.send_message(embed=erro_embed("Saldo insuficiente", "Você não tem moedas suficientes."), ephemeral=True)
            return
        if random.random() < 0.48:
            new_bal = await self.bot.db.change_balance(interaction.guild_id, interaction.user.id, quantidade)
            await interaction.response.send_message(embed=sucesso_embed("Você ganhou", f"Ganhou **{quantidade}**. Saldo: `{new_bal}`."))
        else:
            new_bal = await self.bot.db.change_balance(interaction.guild_id, interaction.user.id, -quantidade)
            await interaction.response.send_message(embed=erro_embed("Você perdeu", f"Perdeu **{quantidade}**. Saldo: `{new_bal}`."))

    @app_commands.command(name="transferir", description="Transferir moedas para outro usuário.")
    @app_commands.guild_only()
    async def transferir(self, interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100000]) -> None:
        if membro.bot or membro.id == interaction.user.id:
            await interaction.response.send_message(embed=erro_embed("Transferência inválida", "Escolha outro usuário real."), ephemeral=True)
            return
        ok = await self.bot.db.transfer(interaction.guild_id, interaction.user.id, membro.id, quantidade)
        if not ok:
            await interaction.response.send_message(embed=erro_embed("Saldo insuficiente", "Você não tem moedas suficientes."), ephemeral=True)
            return
        await interaction.response.send_message(embed=sucesso_embed("Transferência feita", f"Você enviou **{quantidade} {await self.currency(interaction.guild_id)}** para {membro.mention}."))

    @app_commands.command(name="loja", description="Ver loja do servidor.")
    @app_commands.guild_only()
    async def loja(self, interaction: discord.Interaction) -> None:
        items = await self.bot.db.list_shop(interaction.guild_id)
        if not items:
            await interaction.response.send_message(embed=info_embed("Loja", "Nenhum item cadastrado."))
            return
        lines = [f"`{i['id']}` **{i['nome']}** — {i['preco']} {await self.currency(interaction.guild_id)}\n{i['descricao']}" for i in items[:20]]
        await interaction.response.send_message(embed=info_embed("Loja", "\n\n".join(lines)))

    @app_commands.command(name="loja_adicionar", description="Adicionar item à loja.")
    @app_commands.guild_only()
    async def loja_adicionar(self, interaction: discord.Interaction, nome: str, preco: app_commands.Range[int, 1, 1000000], descricao: str = "Item da loja", cargo: Optional[discord.Role] = None) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        if cargo and not await validate_role_management(interaction, cargo): return
        item_id = await self.bot.db.add_shop_item(interaction.guild_id, nome[:64], preco, descricao[:200], cargo.id if cargo else None)
        await interaction.response.send_message(embed=sucesso_embed("Item adicionado", f"ID `{item_id}` — **{nome}** por `{preco}`."), ephemeral=True)

    @app_commands.command(name="loja_remover", description="Remover item da loja.")
    @app_commands.guild_only()
    async def loja_remover(self, interaction: discord.Interaction, item_id: int) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        ok = await self.bot.db.remove_shop_item(interaction.guild_id, item_id)
        await interaction.response.send_message(embed=sucesso_embed("Item removido", f"Item `{item_id}` removido.") if ok else erro_embed("Não encontrado", "Item não encontrado."), ephemeral=True)

    @app_commands.command(name="comprar", description="Comprar item da loja.")
    @app_commands.guild_only()
    async def comprar(self, interaction: discord.Interaction, item_id: int) -> None:
        item = await self.bot.db.get_shop_item(interaction.guild_id, item_id)
        if not item:
            await interaction.response.send_message(embed=erro_embed("Item não encontrado", "Use /loja para ver os itens."), ephemeral=True)
            return
        bal = await self.bot.db.get_balance(interaction.guild_id, interaction.user.id)
        if bal < item["preco"]:
            await interaction.response.send_message(embed=erro_embed("Saldo insuficiente", "Você não tem moedas suficientes."), ephemeral=True)
            return
        await self.bot.db.change_balance(interaction.guild_id, interaction.user.id, -int(item["preco"]))
        await self.bot.db.add_inventory(interaction.guild_id, interaction.user.id, item_id, 1)
        if item["role_id"] and isinstance(interaction.user, discord.Member):
            role = interaction.guild.get_role(int(item["role_id"]))
            if role and interaction.guild.me and role < interaction.guild.me.top_role:
                await interaction.user.add_roles(role, reason="Compra na loja NovaCore")
        await interaction.response.send_message(embed=sucesso_embed("Compra feita", f"Você comprou **{item['nome']}**."))

    @app_commands.command(name="inventario", description="Ver inventário de um usuário.")
    @app_commands.guild_only()
    async def inventario(self, interaction: discord.Interaction, membro: Optional[discord.Member] = None) -> None:
        membro = membro or interaction.user
        items = await self.bot.db.list_inventory(interaction.guild_id, membro.id)
        if not items:
            await interaction.response.send_message(embed=info_embed("Inventário", f"{membro.mention} não possui itens."))
            return
        lines = [f"`x{i['quantidade']}` **{i['nome']}** — {i['descricao']}" for i in items]
        await interaction.response.send_message(embed=info_embed(f"Inventário de {membro.display_name}", "\n".join(lines)))

    @app_commands.command(name="ranking_moedas", description="Ver ranking de moedas.")
    @app_commands.guild_only()
    async def ranking_moedas(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.leaderboard_money(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message(embed=info_embed("Ranking", "Sem saldo registrado."))
            return
        lines = []
        for i, row in enumerate(rows, 1):
            member = interaction.guild.get_member(row["user_id"])
            lines.append(f"**{i}.** {member.mention if member else row['user_id']} — `{row['saldo']}`")
        await interaction.response.send_message(embed=info_embed("Ranking de moedas", "\n".join(lines)))

    @app_commands.command(name="moedas_adicionar", description="Adicionar moedas a um usuário.")
    @app_commands.guild_only()
    async def moedas_adicionar(self, interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 1000000]) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        bal = await self.bot.db.change_balance(interaction.guild_id, membro.id, quantidade)
        await interaction.response.send_message(embed=sucesso_embed("Moedas adicionadas", f"{membro.mention}: saldo `{bal}`."), ephemeral=True)

    @app_commands.command(name="moedas_remover", description="Remover moedas de um usuário.")
    @app_commands.guild_only()
    async def moedas_remover(self, interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 1000000]) -> None:
        if not await require_permissions(interaction, manage_guild=True): return
        bal = await self.bot.db.change_balance(interaction.guild_id, membro.id, -quantidade)
        await interaction.response.send_message(embed=sucesso_embed("Moedas removidas", f"{membro.mention}: saldo `{bal}`."), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economia(bot))
