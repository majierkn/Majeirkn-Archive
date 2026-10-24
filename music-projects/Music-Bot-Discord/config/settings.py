"""Leitura tipada das configurações via pydantic-settings."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord
    discord_token: str
    application_id: int
    log_channel_id: int | None = None

    # Ambiente
    environment: str = "production"

    # Limites globais padrão (podem ser sobrescritos por servidor)
    default_volume: int = 100
    max_queue_size: int = 200
    max_playlists_per_user: int = 20
    max_tracks_per_playlist: int = 500
    play_cooldown_seconds: int = 3
    inactivity_timeout_minutes: int = 5

    # Crossfade
    crossfade_ms: int = 0

    # Last.fm (opcional)
    lastfm_api_key: str | None = None
    lastfm_api_secret: str | None = None

    # SponsorBlock (usa API pública, não precisa de chave)
    sponsorblock_enabled: bool = True

    # Lyrics API (usaremos lyrics.ovh, free)
    lyrics_api_url: str = "https://api.lyrics.ovh/v1"

    @field_validator("default_volume")
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if not 0 <= v <= 150:
            raise ValueError("volume deve estar entre 0 e 150")
        return v

    @field_validator("environment")
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in {"development", "production"}:
            raise ValueError("environment deve ser 'development' ou 'production'")
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
