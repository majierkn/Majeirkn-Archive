"""Parsing de strings de tempo para segundos. Usado pelo comando /seek."""

from __future__ import annotations

import re


def parse_time(time_str: str) -> int | None:
    """
    Converte uma string de tempo para segundos.

    Formatos aceitos:
    - "1:23" → 83
    - "1:23:45" → 5025
    - "83" ou "83s" → 83
    - "1m30s" ou "1m" ou "30s" → segundos equivalentes
    - "1h30m" → 5400

    Retorna None se o formato for inválido.
    """
    time_str = time_str.strip().lower()

    # Formato mm:ss ou hh:mm:ss
    colon_match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if colon_match:
        hours = int(colon_match.group(3) or 0)
        minutes = int(colon_match.group(1)) if colon_match.group(3) else 0
        seconds_part = int(colon_match.group(2))
        if colon_match.group(3):
            # hh:mm:ss
            hours = int(colon_match.group(1))
            minutes = int(colon_match.group(2))
            seconds_part = int(colon_match.group(3))
        else:
            # mm:ss
            hours = 0
            minutes = int(colon_match.group(1))
            seconds_part = int(colon_match.group(2))
        if seconds_part >= 60 or minutes >= 60:
            return None
        return hours * 3600 + minutes * 60 + seconds_part

    # Formato com sufixos: 1h30m20s, 1m30s, 30s, 83
    component_match = re.fullmatch(
        r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?",
        time_str,
    )
    if component_match:
        h = int(component_match.group(1) or 0)
        m = int(component_match.group(2) or 0)
        s = int(component_match.group(3) or 0)
        total = h * 3600 + m * 60 + s
        if total > 0:
            return total

    return None


def format_duration(seconds: int) -> str:
    """Formata segundos como string legível: 1:23 ou 1:23:45."""
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_duration_long(seconds: int) -> str:
    """Formata segundos como '1h 23min 45s' para exibição em embeds."""
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}min")
    if s or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)
