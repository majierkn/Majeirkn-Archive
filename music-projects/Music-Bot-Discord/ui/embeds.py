"""Funções para construção de embeds padronizados do bot."""

from __future__ import annotations

import discord

from core.queue_manager import LoopMode, Track
from utils.helpers import progress_bar, truncate
from utils.time_parser import format_duration, format_duration_long

BOT_COLOR = discord.Color.from_rgb(114, 137, 218)  # azul Discord
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
WARNING_COLOR = discord.Color.orange()
INFO_COLOR = discord.Color.blurple()


def embed_now_playing(
    track: Track,
    elapsed: int,
    volume: int = 100,
    loop_mode: LoopMode = LoopMode.OFF,
    requester: str = "",
) -> discord.Embed:
    """Embed 'Tocando Agora' com barra de progresso."""
    title = truncate(track.title, 60)
    em = discord.Embed(
        title="🎵 Tocando Agora",
        description=f"**[{title}]({track.url})**",
        color=BOT_COLOR,
    )

    if track.thumbnail:
        em.set_thumbnail(url=track.thumbnail)

    if track.is_stream:
        bar_line = "🔴 Transmissão ao vivo"
        duration_line = "∞"
    else:
        bar = progress_bar(elapsed, track.duration_seconds or 1, 20)
        elapsed_fmt = format_duration(elapsed)
        total_fmt = format_duration(track.duration_seconds)
        bar_line = f"`{elapsed_fmt}` {bar} `{total_fmt}`"
        duration_line = format_duration_long(track.duration_seconds)

    em.add_field(name="Progresso", value=bar_line, inline=False)

    if track.uploader:
        em.add_field(name="Canal/Artista", value=truncate(track.uploader, 40), inline=True)

    em.add_field(name="Duração", value=duration_line, inline=True)
    em.add_field(name="Volume", value=f"{volume}%", inline=True)

    loop_labels = {LoopMode.OFF: "Desativado", LoopMode.TRACK: "🔂 Faixa", LoopMode.QUEUE: "🔁 Fila"}
    em.add_field(name="Loop", value=loop_labels[loop_mode], inline=True)

    if requester:
        em.set_footer(text=f"Pedido por {requester}")

    return em


def embed_error(message: str, title: str = "❌ Erro") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=ERROR_COLOR)


def embed_success(message: str, title: str = "✅ Sucesso") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=SUCCESS_COLOR)


def embed_info(message: str, title: str = "ℹ️ Informação") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=INFO_COLOR)


def embed_warning(message: str, title: str = "⚠️ Atenção") -> discord.Embed:
    return discord.Embed(title=title, description=message, color=WARNING_COLOR)


def embed_queue(
    tracks: list[Track],
    current: Track | None,
    page: int,
    total_pages: int,
    loop_mode: LoopMode = LoopMode.OFF,
) -> discord.Embed:
    """Embed de fila paginada."""
    em = discord.Embed(title="📜 Fila de Músicas", color=BOT_COLOR)

    if current:
        em.add_field(
            name="▶️ Tocando Agora",
            value=f"[{truncate(current.title, 50)}]({current.url})",
            inline=False,
        )

    if not tracks:
        em.add_field(name="Fila", value="A fila está vazia.", inline=False)
    else:
        lines = []
        for i, t in enumerate(tracks, start=1):
            dur = format_duration(t.duration_seconds) if t.duration_seconds else "∞"
            lines.append(f"`{i}.` [{truncate(t.title, 45)}]({t.url}) `{dur}`")
        em.add_field(name=f"Próximas ({len(tracks)} faixas)", value="\n".join(lines), inline=False)

    loop_labels = {LoopMode.OFF: "Desativado", LoopMode.TRACK: "🔂 Faixa", LoopMode.QUEUE: "🔁 Fila"}
    em.set_footer(text=f"Página {page}/{total_pages} • Loop: {loop_labels[loop_mode]}")
    return em


def embed_track_added(track: Track, position: int) -> discord.Embed:
    em = discord.Embed(
        title="➕ Adicionado à Fila",
        description=f"**[{truncate(track.title, 60)}]({track.url})**",
        color=SUCCESS_COLOR,
    )
    if track.thumbnail:
        em.set_thumbnail(url=track.thumbnail)
    if track.uploader:
        em.add_field(name="Artista/Canal", value=track.uploader, inline=True)
    if track.duration_seconds:
        em.add_field(name="Duração", value=format_duration_long(track.duration_seconds), inline=True)
    em.add_field(name="Posição na Fila", value=str(position), inline=True)
    if track.requested_by_name:
        em.set_footer(text=f"Pedido por {track.requested_by_name}")
    return em


def embed_playlist_imported(name: str, count: int) -> discord.Embed:
    return discord.Embed(
        title="📂 Playlist Importada",
        description=f"**{name}** — {count} faixas adicionadas à fila.",
        color=SUCCESS_COLOR,
    )


def embed_stats(
    guild_name: str,
    total_tracks: int,
    total_seconds: int,
    top_tracks: list[dict],  # type: ignore[type-arg]
) -> discord.Embed:
    em = discord.Embed(title=f"📊 Estatísticas — {guild_name}", color=BOT_COLOR)
    em.add_field(name="Músicas Tocadas", value=str(total_tracks), inline=True)
    em.add_field(name="Tempo de Reprodução", value=format_duration_long(total_seconds), inline=True)

    if top_tracks:
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, t in enumerate(top_tracks[:10]):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{medal} {truncate(t['title'], 40)} — {t['play_count']}x")
        em.add_field(name="🏆 Top Músicas", value="\n".join(lines), inline=False)

    return em


def embed_history(entries: list[dict]) -> discord.Embed:  # type: ignore[type-arg]
    em = discord.Embed(title="📅 Histórico de Músicas", color=BOT_COLOR)
    if not entries:
        em.description = "Nenhuma música tocada ainda."
    else:
        lines = []
        for i, e in enumerate(entries[:20], 1):
            lines.append(f"`{i}.` [{truncate(e['title'], 45)}]({e['url']})")
        em.description = "\n".join(lines)
    return em


def embed_search_results(results: list[dict]) -> discord.Embed:  # type: ignore[type-arg]
    em = discord.Embed(title="🔍 Resultados da Busca", description="Selecione uma opção abaixo:", color=INFO_COLOR)
    for i, r in enumerate(results[:5], 1):
        title = r.get("title", "Sem título")
        dur = r.get("duration")
        dur_str = format_duration(int(dur)) if dur else "∞"
        em.add_field(name=f"{i}. {truncate(title, 50)}", value=f"Duração: {dur_str}", inline=False)
    return em


def embed_lyrics(title: str, lyrics: str) -> discord.Embed:
    em = discord.Embed(title=f"🎤 Letra — {truncate(title, 50)}", color=BOT_COLOR)
    # Discord field limit = 1024 chars; embed description = 4096
    if len(lyrics) > 3900:
        lyrics = lyrics[:3900] + "\n\n*[letra truncada]*"
    em.description = lyrics
    return em


def embed_exception(error: Exception, context: str = "") -> discord.Embed:
    em = discord.Embed(title="💥 Erro Interno", color=ERROR_COLOR)
    em.add_field(name="Contexto", value=context or "N/A", inline=False)
    em.add_field(name="Erro", value=f"```{str(error)[:500]}```", inline=False)
    return em
