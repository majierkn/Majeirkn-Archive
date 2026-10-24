# 🎵 Bot de Música Discord

Bot de música completo, modular e production-grade para Discord, escrito em Python.

**Funcionalidades:** YouTube, Spotify, SoundCloud, playlists, filtros de áudio, fila persistente, painel interativo, votação, estatísticas e muito mais — 100% dentro do Discord.

---

## 📋 Pré-requisitos

- Python 3.11+
- FFmpeg instalado no sistema
- Uma conta de desenvolvedor Discord com um bot criado

---

## ⚡ Instalação Rápida (VPS Linux / macOS)

```bash
# 1. Clone ou extraia o projeto
cd discord-bot

# 2. Crie e ative um ambiente virtual (opcional, mas recomendado)
python3 -m venv .venv
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Instale o FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg
# macOS (Homebrew):
brew install ffmpeg

# 5. Configure o .env
cp .env.example .env
nano .env  # ou qualquer editor

# 6. Inicie o bot
python bot.py
```

---

## 📱 Instalação no Termux (Android)

```bash
# 1. Atualizar pacotes
pkg update && pkg upgrade

# 2. Instalar dependências do sistema
pkg install python ffmpeg rust git

# Rust é necessário para compilar o pacote davey (DAVE E2E encryption)
# Em dispositivos com pouca RAM (ex: Galaxy M53), limite os jobs de compilação:
export CARGO_BUILD_JOBS=2

# 3. Instalar Python e pip
pip install --upgrade pip

# 4. Clonar/copiar o projeto
cd ~
git clone <seu-repo> discord-bot
cd discord-bot

# 5. Instalar dependências Python
pip install -r requirements.txt

# 6. Configurar .env
cp .env.example .env
nano .env

# 7. Resolver possíveis problemas de DNS no Termux
# Se o bot não conectar, adicione ao .env:
# PYTHONDONTWRITEBYTECODE=1

# 8. Iniciar o bot
python bot.py

# Para manter rodando em background:
nohup python bot.py &
# ou use tmux:
pkg install tmux
tmux new -s bot
python bot.py
# Ctrl+B, D para desconectar da sessão
```

> ⚠️ **Atenção:** Hosts que bloqueiam UDP (ex: tier gratuito da Discloud) impedirão o áudio de funcionar, pois Discord usa UDP para voz.

---

## 🐳 Docker / Docker Compose

```bash
# Configurar .env primeiro
cp .env.example .env
nano .env

# Build e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

---

## ⚙️ Configuração do `.env`

| Variável | Obrigatório | Descrição |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Token do bot (Painel de Desenvolvedor) |
| `APPLICATION_ID` | ✅ | ID da aplicação Discord |
| `LOG_CHANNEL_ID` | ❌ | Canal de texto para logs de erro |
| `ENVIRONMENT` | ❌ | `development` ou `production` (padrão) |
| `DB_PATH` | ❌ | Caminho do banco SQLite (padrão: `data/bot.db`) |
| `LASTFM_API_KEY` | ❌ | Para integração com Last.fm |
| `SPONSORBLOCK_ENABLED` | ❌ | Skip automático de patrocínios (padrão: `true`) |

### Como obter o DISCORD_TOKEN e APPLICATION_ID

1. Acesse [discord.com/developers/applications](https://discord.com/developers/applications)
2. Crie uma nova aplicação ou selecione a existente
3. **APPLICATION_ID:** aba "General Information" → "Application ID"
4. **DISCORD_TOKEN:** aba "Bot" → "Reset Token"
5. Em "Bot" → "Privileged Gateway Intents", ative: **Message Content Intent**, **Server Members Intent**, **Presence Intent**

### Convidar o bot para seu servidor

```
https://discord.com/api/oauth2/authorize?client_id=SEU_APPLICATION_ID&permissions=8&scope=bot%20applications.commands
```

Substitua `SEU_APPLICATION_ID` pelo seu ID real.

---

## 🎵 Comandos Disponíveis

### Reprodução
| Comando | Descrição |
|---|---|
| `/play <busca ou link>` | Toca música por nome ou URL |
| `/pause` | Pausa a reprodução |
| `/resume` | Retoma a reprodução |
| `/stop` | Para e desconecta |
| `/skip` | Pula (com votação se não for DJ) |
| `/seek <mm:ss>` | Avança para um tempo específico |
| `/replay` | Reinicia a música atual |
| `/previous` | Volta para a música anterior |
| `/volume <0-150>` | Ajusta o volume |
| `/nowplaying` | Mostra a música atual |
| `/join` / `/leave` | Entrar/sair do canal de voz |
| `/247` | Modo 24/7 (fica conectado) |
| `/sleeptimer <min>` | Para após X minutos |
| `/lyrics` | Letra da música atual |
| `/history` | Últimas 20 músicas |

### Fila
| Comando | Descrição |
|---|---|
| `/queue` | Exibe a fila paginada |
| `/queue clear` | Limpa a fila |
| `/queue remove <pos>` | Remove uma música |
| `/queue move <de> <para>` | Move uma música |
| `/queue export` | Exporta como JSON/CSV |
| `/queue import <arquivo>` | Importa uma fila exportada |
| `/shuffle` | Embaralha a fila |
| `/loop <off/track/queue>` | Modo de repetição |
| `/autoplay` | Autoplay ao esvaziar fila |

### Playlists
| Comando | Descrição |
|---|---|
| `/playlist create <nome>` | Cria playlist |
| `/playlist save <nome>` | Salva fila como playlist |
| `/playlist load <nome>` | Carrega playlist na fila |
| `/playlist list` | Lista suas playlists |
| `/playlist delete <nome>` | Deleta playlist |
| `/playlist rename <atual> <novo>` | Renomeia playlist |
| `/playlist share <nome> <usuário>` | Compartilha playlist |

### Filtros
| Comando | Descrição |
|---|---|
| `/filter bassboost` | Bass Boost |
| `/filter nightcore` | Nightcore |
| `/filter vaporwave` | Vaporwave |
| `/filter 8d` | 8D Audio |
| `/filter karaoke` | Karaokê (remove vocal) |
| `/filter tremolo` | Tremolo |
| `/filter vibrato` | Vibrato |
| `/filter reset` | Remove todos os filtros |
| `/equalizer <freq> <ganho>` | Ajuste manual de bandas |

### Configuração (Admin)
| Comando | Descrição |
|---|---|
| `/config dj-role <cargo>` | Define cargo de DJ |
| `/config volume-padrao <0-150>` | Volume padrão |
| `/config canal-texto <canal>` | Canal de mensagens do bot |
| `/config max-fila <número>` | Limite de itens na fila |
| `/config 247 <on/off>` | Modo 24/7 |
| `/config ver` | Exibe configurações atuais |

### Admin (Dono do Bot)
| Comando | Descrição |
|---|---|
| `/sync` | Sincroniza slash commands |
| `/ping` | Latência do gateway |
| `/status` | Status e métricas do bot |
| `/restart` | Reinício gracioso |
| `/backup` | Backup do banco de dados |
| `/blacklist add/remove/list` | Gerenciar blacklist |
| `/stats` | Estatísticas do servidor |
| `/topmusicas` | Top 10 músicas |

### Diversão
| Comando | Descrição |
|---|---|
| `/soundboard <som>` | Efeitos sonoros |
| `/quiz musical` | Quiz de adivinhação de música |
| `/reacoes` | Mostra reações da música atual |

---

## 🗄️ Banco de Dados e Migrações

O bot usa SQLite via `aiosqlite`. O banco é criado automaticamente em `data/bot.db` na primeira execução.

Migrações são aplicadas automaticamente na inicialização. Para adicionar uma nova migração:

1. Crie `migrations/002_descricao.sql`
2. O bot aplicará na próxima inicialização

---

## 🧪 Testes

```bash
# Rodar todos os testes
pytest tests/ -v

# Com cobertura
pip install pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

---

## 🔧 Qualidade de Código

```bash
# Lint
ruff check .

# Formatar
ruff format .

# Verificar tipos
mypy bot.py core/ utils/ config/
```

---

## 🏗️ Estrutura do Projeto

```
discord-bot/
├── bot.py                    # Entrada, carrega cogs, on_error global
├── .env                      # Segredos (nunca versionar)
├── .env.example              # Template sem segredos
├── requirements.txt          # Dependências fixadas
├── pyproject.toml            # Config ruff/mypy
├── docker-compose.yml        # Containerização
├── Dockerfile
├── config/
│   └── settings.py           # Leitura tipada do .env
├── cogs/
│   ├── musica.py             # Reprodução
│   ├── fila.py               # Gerenciamento de fila
│   ├── playlists.py          # Playlists personalizadas
│   ├── filtros.py            # Filtros de áudio
│   ├── admin.py              # Administração
│   ├── configuracoes.py      # Configurações por servidor
│   └── diversao.py           # Soundboard, quiz musical
├── core/
│   ├── player.py             # Player yt-dlp + FFmpeg
│   ├── queue_manager.py      # Gerenciador de filas
│   ├── voting.py             # Votação de skip
│   └── database.py           # Repository pattern (aiosqlite)
├── migrations/
│   └── 001_init.sql          # Schema inicial
├── ui/
│   ├── views.py              # Discord UI (botões, menus)
│   └── embeds.py             # Embeds padronizados
├── utils/
│   ├── logger.py             # Logging centralizado
│   ├── time_parser.py        # Parsing de tempo para /seek
│   └── helpers.py            # Funções auxiliares
├── tests/
│   ├── test_queue_manager.py
│   ├── test_time_parser.py
│   └── test_voting.py
└── data/
    └── bot.db                # Banco SQLite (gerado automaticamente)
```

---

## 🚀 Deploy em VPS (Oracle Cloud Free Tier)

```bash
# No servidor (Ubuntu 22.04)
sudo apt update && sudo apt install -y python3.11 python3.11-venv ffmpeg git

git clone <seu-repo> ~/discord-bot
cd ~/discord-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env  # preencher tokens

# Criar serviço systemd para auto-start
sudo tee /etc/systemd/system/discord-bot.service > /dev/null <<EOF
[Unit]
Description=Discord Music Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/discord-bot
ExecStart=/home/$USER/discord-bot/.venv/bin/python bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot
sudo systemctl status discord-bot
```

---

## ⚠️ Limitações Conhecidas

- **Spotify**: não permite streaming direto. O bot busca o equivalente no YouTube com base em metadados.
- **Streams ao vivo**: `/seek` não funciona em streams ao vivo (limitação do FFmpeg/yt-dlp).
- **DAVE (E2E encryption)**: requer o pacote `davey` e Rust para compilar. No Termux, use `CARGO_BUILD_JOBS=2` para evitar OOM.
- **UDP bloqueado**: hosts que bloqueam UDP (ex: tier gratuito da Discloud) impedirão o áudio de funcionar.
- **Rate limits do YouTube**: buscas intensas podem ser temporariamente bloqueadas. Use cookies do browser via yt-dlp se necessário.
