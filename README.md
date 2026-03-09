# Music Bot (Python)

Same Discord music bot as the Node version, written in Python. Plays YouTube audio in voice channels via slash commands.

## Requirements

- **Python 3.10+**
- **FFmpeg** installed and on your PATH (used for audio streaming)
- Discord bot token and application ID

## Setup

1. **Create a virtual environment (recommended):**
   ```bash
   cd music-bot-python
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**  
   - Windows: [ffmpeg.org](https://ffmpeg.org/) or `winget install FFmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` (or your distro’s package manager)

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `DISCORD_TOKEN` — your bot token from the Discord Developer Portal
   - `CLIENT_ID` — your application (bot) ID

## Run

```bash
python main.py
```

## Run with Docker (e.g. Ubuntu server)

The image includes **FFmpeg** and runs as a non-root user.

1. **Build and run with Docker Compose (recommended):**
   ```bash
   # On your server: copy the project and create .env with DISCORD_TOKEN and CLIENT_ID
   docker compose up -d --build
   ```

2. **Or build and run with Docker only:**
   ```bash
   docker build -t music-bot-python .
   docker run -d --restart unless-stopped --env-file .env music-bot-python
   ```

3. **View logs:**
   ```bash
   docker compose logs -f
   ```

## Slash commands

| Command       | Description                          |
|---------------|--------------------------------------|
| `/play query` | Play a song by name or YouTube URL   |
| `/skip`       | Skip the current song                |
| `/stop`       | Stop playback and clear the queue   |
| `/queue`      | Show the current queue               |
| `/pause`      | Pause playback                       |
| `/resume`     | Resume playback                      |
| `/nowplaying` | Show the currently playing song      |

## Tech stack

- **discord.py** (with voice) — Discord API and voice
- **yt-dlp** — YouTube stream URL extraction
- **python-dotenv** — `.env` config
- **FFmpeg** — audio streaming (external binary)

## Project structure

```
music-bot-python/
├── main.py           # Bot and slash commands
├── requirements.txt
├── Dockerfile        # Python + FFmpeg image
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── README.md
```
