import re
from datetime import timedelta

_DURATION_RE = re.compile(r"^(?P<num>\d+)(?P<unit>s|m|h|d)$", re.IGNORECASE)


def parse_duration(value: str) -> timedelta:
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise ValueError("Use formatos como 30s, 10m, 2h ou 7d.")
    num = int(match.group("num"))
    unit = match.group("unit").lower()
    if unit == "s":
        return timedelta(seconds=num)
    if unit == "m":
        return timedelta(minutes=num)
    if unit == "h":
        return timedelta(hours=num)
    if unit == "d":
        return timedelta(days=num)
    raise ValueError("Unidade inválida.")


def human_timedelta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)
