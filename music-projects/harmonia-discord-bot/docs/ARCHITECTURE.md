# Arquitetura

O HarmonIA usa `AutoShardedBot` e cogs por domínio. O `PlayerManager` mantém um `GuildPlayer` isolado por servidor. Metadados persistem em SQLite; URLs de stream são resolvidas novamente pelo yt-dlp antes da reprodução. FFmpeg é executado pelo `discord.py` para transporte Opus.
