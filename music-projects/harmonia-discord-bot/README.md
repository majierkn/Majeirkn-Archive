# HarmonIA

Bot profissional de música para Discord, em **Python 3.12**, com interface pt-BR, comandos slash, filas isoladas por servidor, playlists SQLite e reprodução via yt-dlp + FFmpeg.

## Requisitos

- Python 3.12+
- FFmpeg 6+
- Aplicação Discord com `Message Content` desnecessário; habilite `Server Members` somente se precisar.

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# preencha DISCORD_TOKEN e BOT_OWNER_ID
python -m bot.main
```

Convide o bot com os escopos `bot` e `applications.commands`, além de `Connect`, `Speak`, `Send Messages` e `Embed Links`.

## Comandos principais

`/play`, `/search`, `/nowplaying`, `/stop`, `/leave`, `/queue`, `/skip`, `/remove`, `/clear`, `/shuffle`, `/move`, `/volume`, `/loop`, `/filter`, `/playlist`, `/setup`, `/djrole`, `/canal`, `/stats`. Os comandos de desenvolvimento `!sync`, `!reload` e `!shutdown` são exclusivos do owner.

## Docker

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

O token nunca deve ser commitado. Para produção, use um segredo do ambiente e supervisão com Docker/systemd.
