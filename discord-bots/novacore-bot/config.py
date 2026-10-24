import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0) or None
SYNC_GUILD_ID = int(os.getenv("SYNC_GUILD_ID", "0") or 0) or None
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/novacore.sqlite3")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")
