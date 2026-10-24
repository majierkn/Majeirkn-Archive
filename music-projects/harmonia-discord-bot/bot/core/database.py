from pathlib import Path
import aiosqlite
class Database:
    def __init__(self, path: Path): self.path, self.conn = path, None
    async def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True); self.conn = await aiosqlite.connect(self.path); self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript("""PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS guilds (guild_id INTEGER PRIMARY KEY, guild_name TEXT NOT NULL, dj_role_id INTEGER, music_channel_id INTEGER, default_volume INTEGER DEFAULT 80, created_at REAL DEFAULT(unixepoch()), updated_at REAL DEFAULT(unixepoch()));
        CREATE TABLE IF NOT EXISTS tracks (webpage_url TEXT PRIMARY KEY, title TEXT NOT NULL, uploader TEXT NOT NULL, duration INTEGER NOT NULL DEFAULT 0, thumbnail TEXT, source_type TEXT NOT NULL, last_fetched_at REAL DEFAULT(unixepoch()));
        CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL, guild_id INTEGER, name TEXT NOT NULL, description TEXT DEFAULT '', is_public INTEGER DEFAULT 0, created_at REAL DEFAULT(unixepoch()), updated_at REAL DEFAULT(unixepoch()), UNIQUE(owner_id,name));
        CREATE TABLE IF NOT EXISTS playlist_tracks (id INTEGER PRIMARY KEY AUTOINCREMENT, playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE, webpage_url TEXT NOT NULL, title TEXT NOT NULL, uploader TEXT NOT NULL, duration INTEGER DEFAULT 0, thumbnail TEXT, source_type TEXT NOT NULL, position INTEGER NOT NULL, UNIQUE(playlist_id,webpage_url));
        CREATE TABLE IF NOT EXISTS queue_state (guild_id INTEGER NOT NULL, position INTEGER NOT NULL, webpage_url TEXT NOT NULL, title TEXT NOT NULL, uploader TEXT NOT NULL, duration INTEGER DEFAULT 0, thumbnail TEXT, source_type TEXT NOT NULL, requested_by_id INTEGER, PRIMARY KEY(guild_id,position));"""); await self.conn.commit()
    async def close(self):
        if self.conn: await self.conn.close()
    async def ensure_guild(self, guild_id, name):
        await self.conn.execute("INSERT INTO guilds(guild_id,guild_name) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET guild_name=excluded.guild_name,updated_at=unixepoch()", (guild_id,name)); await self.conn.commit()
    async def create_playlist(self, owner_id, guild_id, name, description=''):
        cur=await self.conn.execute("INSERT INTO playlists(owner_id,guild_id,name,description) VALUES(?,?,?,?)",(owner_id,guild_id,name,description)); await self.conn.commit(); return cur.lastrowid
    async def list_playlists(self, owner_id, guild_id):
        cur=await self.conn.execute("SELECT * FROM playlists WHERE owner_id=? AND (guild_id=? OR guild_id IS NULL) ORDER BY name",(owner_id,guild_id)); return await cur.fetchall()
