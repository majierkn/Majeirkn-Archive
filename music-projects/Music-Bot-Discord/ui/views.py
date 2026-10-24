"""Views interativas (botões, menus) para o painel de controle do bot."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import ButtonStyle, ui

from core.queue_manager import LoopMode, Track, queue_registry
from utils.helpers import chunk_list

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NowPlayingView — painel principal persistente
# ---------------------------------------------------------------------------


class NowPlayingView(ui.View):
    """
    View persistente com botões de controle de reprodução.
    Sobrevive a reinícios do bot (timeout=None + bot.add_view no setup_hook).
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @ui.button(label="⏯️", style=ButtonStyle.primary, custom_id="np_playpause")
    async def playpause(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        vc = interaction.guild.voice_client
        if vc is None:
            await interaction.followup.send("❌ Não estou em um canal de voz.", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            from core.player import get_player_state
            get_player_state(interaction.guild.id).on_pause()
        elif vc.is_paused():
            vc.resume()
            from core.player import get_player_state
            get_player_state(interaction.guild.id).on_resume()

    @ui.button(label="⏭️", style=ButtonStyle.secondary, custom_id="np_skip")
    async def skip(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        else:
            await interaction.followup.send("❌ Nada está tocando.", ephemeral=True)

    @ui.button(label="⏹️", style=ButtonStyle.danger, custom_id="np_stop")
    async def stop(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        await q.clear()
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await vc.disconnect()
        await interaction.followup.send("⏹️ Reprodução encerrada.", ephemeral=True)

    @ui.button(label="🔀", style=ButtonStyle.secondary, custom_id="np_shuffle")
    async def shuffle(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        await q.shuffle()
        await interaction.followup.send("🔀 Fila embaralhada!", ephemeral=True)

    @ui.button(label="🔁", style=ButtonStyle.secondary, custom_id="np_loop")
    async def loop(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        modes = [LoopMode.OFF, LoopMode.TRACK, LoopMode.QUEUE]
        next_idx = (modes.index(q.loop_mode) + 1) % len(modes)
        q.loop_mode = modes[next_idx]
        labels = {LoopMode.OFF: "desativado", LoopMode.TRACK: "🔂 faixa", LoopMode.QUEUE: "🔁 fila"}
        await interaction.followup.send(f"Loop: **{labels[q.loop_mode]}**", ephemeral=True)

    @ui.button(label="🔉", style=ButtonStyle.secondary, custom_id="np_vol_down")
    async def vol_down(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        from core.player import get_player_state
        state = get_player_state(interaction.guild.id)
        vc = interaction.guild.voice_client
        new_vol = max(0.0, state.volume - 0.1)
        state.volume = new_vol
        if vc and vc.source:
            if hasattr(vc.source, "volume"):
                vc.source.volume = new_vol
        await interaction.followup.send(f"🔉 Volume: **{int(new_vol * 100)}%**", ephemeral=True)

    @ui.button(label="🔊", style=ButtonStyle.secondary, custom_id="np_vol_up")
    async def vol_up(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer()
        if interaction.guild is None:
            return
        from core.player import get_player_state
        state = get_player_state(interaction.guild.id)
        vc = interaction.guild.voice_client
        new_vol = min(1.5, state.volume + 0.1)
        state.volume = new_vol
        if vc and vc.source:
            if hasattr(vc.source, "volume"):
                vc.source.volume = new_vol
        await interaction.followup.send(f"🔊 Volume: **{int(new_vol * 100)}%**", ephemeral=True)

    @ui.button(label="❤️", style=ButtonStyle.secondary, custom_id="np_favorite")
    async def favorite(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            return
        q = queue_registry.get(interaction.guild.id)
        current = q.current
        if current is None:
            await interaction.followup.send("❌ Nada está tocando.", ephemeral=True)
            return
        from core.database import Database
        db = await Database.get()
        # Busca ou cria playlist Favoritos do usuário
        pl = await db.get_playlist(interaction.user.id, "❤️ Favoritos")
        if pl is None:
            pl_id = await db.create_playlist(interaction.user.id, "❤️ Favoritos", visibility="privada")
        else:
            pl_id = pl.id
        await db.add_track_to_playlist(
            pl_id, current.title, current.url, current.duration_seconds, current.thumbnail
        )
        await interaction.followup.send(
            f"❤️ **{current.title}** adicionada aos seus Favoritos!", ephemeral=True
        )


# ---------------------------------------------------------------------------
# QueueView — fila paginada
# ---------------------------------------------------------------------------


class QueueView(ui.View):
    def __init__(self, tracks: list[Track], current: Track | None, loop_mode: LoopMode) -> None:
        super().__init__(timeout=120)
        self.pages = chunk_list(tracks, 10)
        self.page = 0
        self.current = current
        self.loop_mode = loop_mode
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= len(self.pages) - 1

    def _build_embed(self) -> discord.Embed:
        from ui.embeds import embed_queue
        page_tracks = self.pages[self.page] if self.pages else []
        return embed_queue(
            page_tracks, self.current, self.page + 1, max(len(self.pages), 1), self.loop_mode
        )

    @ui.button(label="⏮️ Anterior", style=ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        self.page = max(0, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @ui.button(label="Próxima ⏭️", style=ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)


# ---------------------------------------------------------------------------
# SearchResultsView — seleção de resultado de busca
# ---------------------------------------------------------------------------


class SearchResultsSelect(ui.Select):  # type: ignore[type-arg]
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = results
        options = []
        for i, r in enumerate(results[:5]):
            title = r.get("title", "Sem título")[:100]
            options.append(discord.SelectOption(label=title, value=str(i)))
        super().__init__(placeholder="Escolha uma música…", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        idx = int(self.values[0])
        result = self.results[idx]
        self.view.chosen = result  # type: ignore[union-attr]
        self.view.stop()  # type: ignore[union-attr]
        await interaction.response.defer()


class SearchResultsView(ui.View):
    def __init__(self, results: list[dict[str, Any]]) -> None:
        super().__init__(timeout=30)
        self.chosen: dict[str, Any] | None = None
        self.add_item(SearchResultsSelect(results))

    @ui.button(label="Cancelar", style=ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        self.chosen = None
        self.stop()
        await interaction.response.defer()


# ---------------------------------------------------------------------------
# VoteView — botão de voto de skip
# ---------------------------------------------------------------------------


class VoteSkipView(ui.View):
    def __init__(self, session: Any) -> None:  # session: VoteSession
        super().__init__(timeout=30)
        self.session = session

    @ui.button(label="👍 Votar no Skip", style=ButtonStyle.primary, custom_id="vote_skip")
    async def vote_btn(self, interaction: discord.Interaction, button: ui.Button) -> None:  # type: ignore[type-arg]
        from core.voting import VotingManager
        already = self.session.add_vote(interaction.user.id)
        if already:
            await interaction.response.send_message("✋ Você já votou!", ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ Voto registrado! ({self.session.progress})", ephemeral=True
        )
        if self.session.passed:
            self.stop()
