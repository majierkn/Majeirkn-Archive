-- Migração 001: Schema inicial

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    dj_role_id INTEGER,
    default_volume INTEGER DEFAULT 100,
    text_channel_id INTEGER,
    max_queue_size INTEGER DEFAULT 200,
    language TEXT DEFAULT 'pt-BR',
    mode_247 BOOLEAN DEFAULT 0,
    crossfade_ms INTEGER DEFAULT 0,
    inactivity_timeout_minutes INTEGER DEFAULT 5,
    blocked_keywords TEXT DEFAULT '',
    play_cooldown_seconds INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    visibility TEXT CHECK(visibility IN ('publica','privada')) DEFAULT 'privada',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    duration_seconds INTEGER,
    thumbnail TEXT,
    position INTEGER
);

CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blacklist (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reason TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS persistent_queues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    duration_seconds INTEGER,
    thumbnail TEXT,
    requested_by_id INTEGER,
    requested_by_name TEXT
);

CREATE TABLE IF NOT EXISTS play_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    play_count INTEGER DEFAULT 1,
    total_seconds INTEGER DEFAULT 0,
    UNIQUE(guild_id, url)
);

CREATE TABLE IF NOT EXISTS guild_play_totals (
    guild_id INTEGER PRIMARY KEY,
    total_tracks INTEGER DEFAULT 0,
    total_seconds INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
