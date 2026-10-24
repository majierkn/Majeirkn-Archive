"""Cog de playlists personalizadas."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import get_settings
from core.database import Database
from core.queue_manager import Track, queue_registry
from ui.embeds import embed_error, embed_info, embed_success, embed_warning

logger = logging.getLogger(__name__)
settings = get_settings()


class Playlists(commands.Cog, name="Playlists"):
    """Cog responsável pelas playlists personalizadas dos usuários."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _ensure_favorites(self, user_id: int) -> int:
        """Garante que o usuário tem a playlist Favoritos. Retorna o ID."""
        db = await Database.get()
        pl = await db.get_playlist(user_id, "❤️ Favoritos")
        if pl is None:
            return await db.create_playlist(user_id, "❤️ Favoritos", visibility="privada")
        return pl.id

    playlist_group = app_commands.Group(name="playlist", description="Gerenciamento de playlists.")

    @playlist_group.command(name="create", description="Cria uma nova playlist.")
    @app_commands.describe(nome="Nome da playlist", visibilidade="publica ou privada")
    @app_commands.choices(visibilidade=[
        app_commands.Choice(name="Privada", value="privada"),
        app_commands.Choice(name="Pública", value="publica"),
    ])
    async def playlist_create(
        self,
        interaction: discord.Interaction,
        nome: str,
        visibilidade: str = "privada",
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        db = await Database.get()

        count = await db.count_user_playlists(interaction.user.id)
        if count >= settings.max_playlists_per_user:
            await interaction.followup.send(
                embed=embed_error(f"❌ Limite de {settings.max_playlists_per_user} playlists atingido."),
                ephemeral=True,
            )
            return

        existing = await db.get_playlist(interaction.user.id, nome)
        if existing:
            await interaction.followup.send(embed=embed_error(f"❌ Você já tem uma playlist chamada **{nome}**."), ephemeral=True)
            return

        guild_id = interaction.guild.id if interaction.guild else None
        await db.create_playlist(interaction.user.id, nome, guild_id=guild_id, visibility=visibilidade)
        await interaction.followup.send(embed=embed_success(f"✅ Playlist **{nome}** criada!"), ephemeral=True)

    @playlist_group.command(name="save", description="Salva a fila atual como uma playlist.")
    @app_commands.describe(nome="Nome da playlist")
    async def playlist_save(self, interaction: discord.Interaction, nome: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return

        q = queue_registry.get(interaction.guild.id)
        tracks = q.queue
        if q.current:
            tracks = [q.current] + tracks

        if not tracks:
            await interaction.followup.send(embed=embed_error("❌ A fila está vazia."), ephemeral=True)
            return

        db = await Database.get()
        pl = await db.get_playlist(interaction.user.id, nome)
        if pl is None:
            count = await db.count_user_playlists(interaction.user.id)
            if count >= settings.max_playlists_per_user:
                await interaction.followup.send(
                    embed=embed_error(f"❌ Limite de {settings.max_playlists_per_user} playlists atingido."),
                    ephemeral=True,
                )
                return
            pl_id = await db.create_playlist(interaction.user.id, nome, guild_id=interaction.guild.id)
        else:
            pl_id = pl.id
            await db.clear_playlist_tracks(pl_id)

        for track in tracks[:settings.max_tracks_per_playlist]:
            await db.add_track_to_playlist(pl_id, track.title, track.url, track.duration_seconds, track.thumbnail)

        await interaction.followup.send(
            embed=embed_success(f"💾 Fila salva como playlist **{nome}** ({len(tracks)} faixas)."),
            ephemeral=True,
        )

    @playlist_group.command(name="load", description="Carrega uma playlist na fila.")
    @app_commands.describe(nome="Nome da playlist")
    async def playlist_load(self, interaction: discord.Interaction, nome: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            return

        db = await Database.get()
        pl = await db.get_playlist(interaction.user.id, nome)
        if pl is None:
            # Tentar playlist pública do servidor
            public_pls = await db.list_public_playlists(interaction.guild.id)
            pl = next((p for p in public_pls if p.name == nome), None)
        if pl is None:
            await interaction.followup.send(embed=embed_error(f"❌ Playlist **{nome}** não encontrada."), ephemeral=True)
            return

        track_rows = await db.get_playlist_tracks(pl.id)
        if not track_rows:
            await interaction.followup.send(embed=embed_error("❌ Esta playlist está vazia."), ephemeral=True)
            return

        q = queue_registry.get(interaction.guild.id)
        tracks = [
            Track(
                title=t.title,
                url=t.url,
                webpage_url=t.url,
                duration_seconds=t.duration_seconds or 0,
                thumbnail=t.thumbnail,
                requested_by_id=interaction.user.id,
                requested_by_name=str(interaction.user.display_name),
            )
            for t in track_rows
        ]
        added = await q.add_many(tracks)
        await interaction.followup.send(
            embed=embed_success(f"📂 Playlist **{nome}** carregada! {added} faixas adicionadas à fila.")
        )

        vc = interaction.guild.voice_client
        if vc and not vc.is_playing() and not vc.is_paused():
            musica_cog = self.bot.cogs.get("Música")
            if musica_cog:
                await musica_cog._play_next(interaction.guild.id)  # type: ignore[attr-defined]

    @playlist_load.autocomplete("nome")
    async def playlist_load_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        db = await Database.get()
        pls = await db.list_playlists(interaction.user.id)
        return [
            app_commands.Choice(name=p.name, value=p.name)
            for p in pls
            if current.lower() in p.name.lower()
        ][:25]

    @playlist_group.command(name="list", description="Lista suas playlists.")
    async def playlist_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        db = await Database.get()
        pls = await db.list_playlists(interaction.user.id)

        if not pls:
            await interaction.followup.send(embed=embed_info("Você não tem nenhuma playlist ainda."), ephemeral=True)
            return

        lines = []
        for p in pls:
            vis = "🌐" if p.visibility == "publica" else "🔒"
            count = await db.count_playlist_tracks(p.id)
            lines.append(f"{vis} **{p.name}** — {count} faixas")

        em = discord.Embed(title="📂 Suas Playlists", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.followup.send(embed=em, ephemeral=True)

    @playlist_group.command(name="delete", description="Deleta uma playlist.")
    @app_commands.describe(nome="Nome da playlist")
    async def playlist_delete(self, interaction: discord.Interaction, nome: str) -> None:
        await interaction.response.defer(ephemeral=True)
        db = await Database.get()
        pl = await db.get_playlist(interaction.user.id, nome)
        if pl is None:
            await interaction.followup.send(embed=embed_error(f"❌ Playlist **{nome}** não encontrada."), ephemeral=True)
            return
        await db.delete_playlist(pl.id)
        await interaction.followup.send(embed=embed_success(f"🗑️ Playlist **{nome}** deletada."), ephemeral=True)

    @playlist_delete.autocomplete("nome")
    async def playlist_delete_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        db = await Database.get()
        pls = await db.list_playlists(interaction.user.id)
        return [
            app_commands.Choice(name=p.name, value=p.name)
            for p in pls
            if current.lower() in p.name.lower()
        ][:25]

    @playlist_group.command(name="rename", description="Renomeia uma playlist.")
    @app_commands.describe(nome_atual="Nome atual", novo_nome="Novo nome")
    async def playlist_rename(
        self, interaction: discord.Interaction, nome_atual: str, novo_nome: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        db = await Database.get()
        pl = await db.get_playlist(interaction.user.id, nome_atual)
        if pl is None:
            await interaction.followup.send(embed=embed_error(f"❌ Playlist **{nome_atual}** não encontrada."), ephemeral=True)
            return
        existing = await db.get_playlist(interaction.user.id, novo_nome)
        if existing:
            await interaction.followup.send(embed=embed_error(f"❌ Você já tem uma playlist chamada **{novo_nome}**."), ephemeral=True)
            return
        await db.rename_playlist(pl.id, novo_nome)
        await interaction.followup.send(embed=embed_success(f"✏️ Playlist renomeada para **{novo_nome}**."), ephemeral=True)

    @playlist_group.command(name="share", description="Compartilha uma playlist com outro usuário.")
    @app_commands.describe(nome="Nome da playlist", usuario="Usuário para compartilhar")
    async def playlist_share(
        self, interaction: discord.Interaction, nome: str, usuario: discord.User
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        db = await Database.get()
        pl = await db.get_playlist(interaction.user.id, nome)
        if pl is None:
            await interaction.followup.send(embed=embed_error(f"❌ Playlist **{nome}** não encontrada."), ephemeral=True)
            return

        tracks = await db.get_playlist_tracks(pl.id)
        guild_id = interaction.guild.id if interaction.guild else None

        # Verificar limite do usuário destino
        target_count = await db.count_user_playlists(usuario.id)
        if target_count >= settings.max_playlists_per_user:
            await interaction.followup.send(
                embed=embed_error(f"❌ {usuario.display_name} atingiu o limite de playlists."),
                ephemeral=True,
            )
            return

        new_name = f"{nome} (de {interaction.user.display_name})"
        new_id = await db.create_playlist(usuario.id, new_name, guild_id=guild_id)
        for t in tracks:
            await db.add_track_to_playlist(new_id, t.title, t.url, t.duration_seconds, t.thumbnail)

        await interaction.followup.send(
            embed=embed_success(f"📤 Playlist **{nome}** compartilhada com {usuario.mention}!"),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Playlists(bot))
