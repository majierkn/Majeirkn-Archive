from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    discord_token: str = Field(...)
    bot_owner_id: int = Field(...)
    bot_name: str = "HarmonIA"
    bot_prefix: str = "!"
    bot_status: str = "ouvindo /play"
    database_path: Path = Path("./data/harmonia.db")
    ffmpeg_path: str = "ffmpeg"
    ytdlp_cookiefile: str | None = None
    default_volume: int = Field(80, ge=0, le=200)
    max_queue_size: int = Field(500, ge=1)
    max_playlist_size: int = Field(200, ge=1)
    inactivity_timeout: int = Field(300, ge=30)
    track_cache_ttl: int = Field(3600, ge=60)
    search_cache_ttl: int = Field(300, ge=30)
    track_cache_max: int = Field(1000, ge=10)
    search_cache_max: int = Field(200, ge=10)
    shard_count: int | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    log_file: Path | None = None
    debug: bool = False
    sync_commands_on_startup: bool = False
    test_guild_id: int | None = None
    @field_validator("database_path", mode="before")
    @classmethod
    def make_data_dir(cls, v):
        p = Path(v); p.parent.mkdir(parents=True, exist_ok=True); return p
    @field_validator("log_file", mode="before")
    @classmethod
    def make_log_dir(cls, v):
        if not v: return None
        p = Path(v); p.parent.mkdir(parents=True, exist_ok=True); return p

_settings = None
def get_settings() -> Settings:
    global _settings
    if _settings is None: _settings = Settings()
    return _settings
