# Changelog

Todas as mudanças notáveis neste projeto serão documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.0] — 2025-07-14

### Adicionado
- **Player de Música** completo com yt-dlp + FFmpeg
  - Suporte a YouTube, YouTube Music, Spotify (via busca), SoundCloud, links diretos, rádios/streams, arquivos Discord
  - Importação de playlists inteiras (YouTube e Spotify) com barra de progresso
  - Integração com SponsorBlock (skip automático de patrocínios/intros)
  - Crossfade configurável entre faixas
  - Normalização de volume (loudness)
- **Controles**: `/play`, `/pause`, `/resume`, `/stop`, `/skip`, `/seek`, `/replay`, `/previous`, `/volume`, `/nowplaying`
- **Modos especiais**: `/247`, `/sleeptimer`
- **Fila** persistente com `/queue`, `/queue clear`, `/queue remove`, `/queue move`, `/shuffle`, `/loop`, `/autoplay`, `/queue export`, `/queue import`
- **Playlists** personalizadas com `/playlist create/save/load/list/delete/rename/share`
  - Escopo público/privado
  - Playlist especial "❤️ Favoritos" automática
  - Autocomplete nos comandos
- **Painel de controle interativo** com botões persistentes (⏯️ ⏭️ ⏹️ 🔀 🔁 🔉 🔊 ❤️)
- **Filtros de áudio**: bassboost, nightcore, vaporwave, 8d, karaoke, tremolo, vibrato, reset
- **Equalizador** por banda de frequência (`/equalizer`)
- **Voz inteligente**: auto-pause quando canal fica vazio, auto-resume ao voltar
- **Votação democrática** de skip para usuários sem DJ
- **Configuração por servidor**: `/config dj-role/volume-padrao/canal-texto/max-fila/247`
- **Moderação**: `/blacklist add/remove/list`, filtro de palavras-chave na busca
- **Estatísticas**: `/stats`, `/topmusicas`, `/history`, `/lyrics`
- **Diversão**: `/soundboard`, `/quiz musical`, reações 👍/👎 nas mensagens
- **Admin**: `/sync`, `/ping`, `/status`, `/restart`, `/backup`
- **Privacidade (LGPD)**: `/meusdados excluir`
- Suporte a **DAVE** (E2E voice encryption) via `davey`
- Suporte a **Android/Termux** e **VPS Linux** / Docker
- Banco de dados SQLite via `aiosqlite` com migrações versionadas
- Logging com `RotatingFileHandler` por nível de ambiente
- CI com GitHub Actions (lint + testes)
- Suite de testes `pytest` cobrindo fila, votação e parsing de tempo
