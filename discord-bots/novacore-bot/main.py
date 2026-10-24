import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from config import DATABASE_PATH, DISCORD_TOKEN, OWNER_ID, SYNC_GUILD_ID
from database.database import Database
from utils.embeds import erro_embed

COGS = [
    "cogs.logs",
    "cogs.configuracao",
    "cogs.automod",
    "cogs.boas_vindas",
    "cogs.moderacao",
    "cogs.tickets",
    "cogs.niveis",
    "cogs.economia",
    "cogs.utilidade",
    "cogs.diversao",
    "cogs.sorteios",
    "cogs.musica",
    "cogs.ajuda",
]

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("NovaCore")


class NovaCoreBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.messages = True
        intents.reactions = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            owner_id=OWNER_ID,
            help_command=None,
        )
        self.db: Database | None = None

    async def setup_hook(self) -> None:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(DATABASE_PATH)
        await self.db.connect()
        await self.db.init_schema()

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("Cog carregada: %s", cog)
            except Exception:
                log.exception("Falha ao carregar cog: %s", cog)

        try:
            if SYNC_GUILD_ID:
                guild = discord.Object(id=SYNC_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info("%s comandos sincronizados no servidor de teste %s.", len(synced), SYNC_GUILD_ID)
            else:
                synced = await self.tree.sync()
                log.info("%s comandos slash sincronizados globalmente.", len(synced))
        except Exception:
            log.exception("Falha ao sincronizar comandos slash.")

    async def close(self) -> None:
        if self.db:
            await self.db.close()
        await super().close()


bot = NovaCoreBot()


@bot.event
async def on_ready() -> None:
    assert bot.user is not None
    log.info("NovaCore Bot online como %s (%s)", bot.user, bot.user.id)
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="/ajuda | NovaCore Bot")
    )


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    original = getattr(error, "original", error)
    log.exception("Erro em comando slash", exc_info=original)

    if isinstance(error, discord.app_commands.MissingPermissions):
        embed = erro_embed("Permissão insuficiente", "Você não tem permissão para usar este comando.")
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        embed = erro_embed("Permissão do bot insuficiente", "Eu não tenho as permissões necessárias para executar isso.")
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        embed = erro_embed("Aguarde", f"Use novamente em `{error.retry_after:.1f}s`.")
    elif isinstance(original, discord.Forbidden):
        embed = erro_embed("Acesso negado", "O Discord negou a ação. Verifique minhas permissões e hierarquia de cargos.")
    else:
        embed = erro_embed("Erro inesperado", "Algo deu errado ao executar o comando. Veja os logs do terminal.")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        log.exception("Não consegui enviar a mensagem de erro ao usuário.")


async def main() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN não encontrado. Configure o token no arquivo .env ou nas variáveis de ambiente.")
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot encerrado manualmente pelo terminal.")
