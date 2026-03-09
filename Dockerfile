# Music bot (Python) — Ubuntu/Debian with Python + FFmpeg
FROM python:3.11-slim-bookworm

# Install FFmpeg (required for discord.py voice streaming)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Run as non-root
RUN useradd -m -u 1000 bot && chown -R bot:bot /app
USER bot

CMD ["python", "-u", "main.py"]
