"""Ponto de entrada do bot de música Discord."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

import discord
from discord.ext import commands

# Carregar variáveis de ambiente antes de tudo
from dotenv import load_dotenv
load_dotenv()

from config.settings import get_settings
from utils.logger import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.environment)
logger = get_logger("bot")

# Verificar dependência davey (DAVE — E2E voice encryption)
try:
    import davey  # type: ignore[import]
    logger.info("davey carregado com sucesso — suporte a DAVE (E2E) ativo.")
except ImportError:
    logger.warning(
        "⚠️ davey não está instalado. Suporte ao protocolo DAVE (criptografia de voz E2E) desativado. "
        "Instale com: pip install davey (requer Rust no Termux: pkg install rust)"
    )

COGS = [
    "cogs.musica",
    "cogs.fila",
    "cogs.playlists",
    "cogs.filtros",
    "cogs.admin",
    "cogs.configuracoes",
    "cogs.diversao",
]


class MusicBot(commands.Bot):
    """Bot de música completo para Discord."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=settings.application_id,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        """Carrega cogs e registra views persistentes."""
        logger.info("Iniciando setup_hook…")

        # Inicializar banco de dados
        from core.database import Database
        await Database.get()
        logger.info("Banco de dados iniciado.")

        # Carregar cogs
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info("Cog carregado: %s", cog)
            except Exception as exc:
                logger.exception("Falha ao carregar cog %s: %s", cog, exc)

        # Registrar views persistentes (sobrevivem a reinícios)
        from ui.views import NowPlayingView
        self.add_view(NowPlayingView())
        logger.info("Views persistentes registradas.")

        logger.info("setup_hook concluído.")

    async def on_ready(self) -> None:
        logger.info("Bot online como %s (ID: %s)", self.user, self.user.id if self.user else "N/A")
        logger.info("Servidores: %d", len(self.guilds))
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="🎵 /play para começar")
        )

        # Restaurar filas persistentes
        await self._restore_queues()

    async def _restore_queues(self) -> None:
        """Restaura filas salvas no banco após reinício."""
        from core.database import Database
        from core.queue_manager import Track, queue_registry

        db = await Database.get()
        for guild in self.guilds:
            tracks_data = await db.load_queue(guild.id)
            if tracks_data:
                q = queue_registry.get(guild.id)
                q.load_from_dicts(tracks_data)
                logger.info("Fila restaurada para o servidor %s (%d faixas).", guild.name, len(tracks_data))

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Gerencia auto-pause e auto-desconexão."""
        guild = member.guild
        vc = guild.voice_client

        if vc is None or member.bot:
            return

        # Bot saiu do canal
        if not vc.channel:
            return

        from utils.helpers import member_voice_count
        human_count = member_voice_count(vc.channel)  # type: ignore[arg-type]

        from core.player import get_player_state
        state = get_player_state(guild.id)

        if human_count == 0:
            # Canal ficou vazio → pausar
            if vc.is_playing():
                vc.pause()
                state.on_pause()
                logger.info("Canal vazio em %s — reprodução pausada automaticamente.", guild.name)
        else:
            # Alguém entrou → retomar se pausado por inatividade
            if vc.is_paused():
                vc.resume()
                state.on_resume()
                logger.info("Membro entrou em %s — reprodução retomada.", guild.name)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        from core.database import Database
        db = await Database.get()
        await db.ensure_guild(guild.id)
        logger.info("Entrei no servidor: %s (%d)", guild.name, guild.id)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        """Captura erros de slash commands e exibe mensagem amigável."""
        from ui.embeds import embed_error

        if isinstance(error, discord.app_commands.CommandOnCooldown):
            msg = f"⏳ Aguarde **{error.retry_after:.1f}s** antes de usar este comando novamente."
        elif isinstance(error, discord.app_commands.MissingPermissions):
            msg = "❌ Você não tem permissão para usar este comando."
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            msg = f"❌ O bot não tem as permissões necessárias: {', '.join(error.missing_permissions)}"
        else:
            msg = f"❌ Erro inesperado: {error}"
            logger.exception("Erro em slash command: %s", error)
            await self._send_to_log_channel(error, interaction)

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed_error(msg), ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed_error(msg), ephemeral=True)
        except Exception:
            pass

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        """Captura erros de eventos e envia ao canal de log."""
        import traceback
        exc = sys.exc_info()
        logger.exception("Erro no evento %s: %s", event_method, exc[1])
        if exc[1]:
            await self._send_to_log_channel(exc[1], context=f"Evento: {event_method}")

    async def _send_to_log_channel(
        self,
        error: BaseException,
        interaction: discord.Interaction | None = None,
        context: str = "",
    ) -> None:
        """Envia embed de erro ao canal de log configurado."""
        if not settings.log_channel_id:
            return
        channel = self.get_channel(settings.log_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        from ui.embeds import embed_exception
        ctx_str = context
        if interaction:
            ctx_str = f"Comando: `/{interaction.command.name if interaction.command else 'N/A'}`  Servidor: {interaction.guild}"
        try:
            await channel.send(embed=embed_exception(error, ctx_str))
        except Exception:
            pass

    async def close(self) -> None:
        """Graceful shutdown: salva filas antes de desligar."""
        logger.info("Iniciando desligamento gracioso…")
        from core.database import Database
        from core.queue_manager import queue_registry

        db = await Database.get()
        for guild in self.guilds:
            q = queue_registry.get(guild.id)
            tracks = q.to_dicts()
            try:
                await db.save_queue(guild.id, tracks)
            except Exception:
                pass

        await db.close()
        await super().close()
        logger.info("Bot desligado.")


async def main() -> None:
    bot = MusicBot()

    # Handle SIGTERM graciosamente (Docker, systemd, etc.)
    loop = asyncio.get_event_loop()

    def _handle_signal() -> None:
        logger.info("Sinal de término recebido.")
        loop.create_task(bot.close())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass  # Windows não suporta add_signal_handler

    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
