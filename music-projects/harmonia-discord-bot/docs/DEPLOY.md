# Deploy

Para Docker, copie `.env.example` para `.env`, preencha o token e execute `docker compose -f docker/docker-compose.yml up -d --build`. Para VPS sem Docker, instale Python 3.12, FFmpeg 6+, dependências e execute `python -m bot.main` sob systemd ou outro supervisor.
