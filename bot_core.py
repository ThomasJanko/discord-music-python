"""
Core music bot: MusicBot, GuildQueue, Song, and yt-dlp helpers.
"""
import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import discord
from discord.ext import commands
import yt_dlp

# ─── YT-DLP options (audio only, no download) ─────────────────────────────────
YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

MSG_NOTHING_PLAYING = "❌ Nothing is playing."


@dataclass
class Song:
    title: str
    url: str
    duration: str


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None or seconds <= 0:
        return "?:??"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def is_youtube_url(query: str) -> bool:
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", query))


def _get_stream_url_sync(query: str, is_search: bool) -> dict:
    """Blocking: get video info and stream URL."""
    opts = {**YDL_OPTS}
    if is_search:
        opts["default_search"] = "ytsearch1"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    if info is None:
        raise ValueError("No result")
    if "entries" in info and info["entries"]:
        info = info["entries"][0]
    if not info.get("url") and not info.get("formats"):
        raise ValueError("No playable format")
    url = info.get("url")
    if not url and info.get("formats"):
        for f in info.get("formats", []):
            if f.get("url"):
                url = f["url"]
                break
    if not url:
        raise ValueError("Could not get stream URL")
    duration_sec = info.get("duration")
    return {
        "title": info.get("title") or "Unknown",
        "url": url,
        "duration": format_duration(duration_sec),
    }


async def get_stream_url(query: str, is_search: bool = False) -> dict:
    """Async wrapper so yt-dlp doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: _get_stream_url_sync(query, is_search)
    )


# ─── Guild queue state ────────────────────────────────────────────────────────
class GuildQueue:
    def __init__(self, text_channel: discord.TextChannel):
        self.songs: list[Song] = []
        self.text_channel = text_channel
        self.current_song: Optional[Song] = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self._idle_task: Optional[asyncio.Task] = None
        self.volume: float = 1.0  # 0.0 to 1.0
        self.current_volume_source: Optional[discord.PCMVolumeTransformer] = None

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

    def is_empty(self) -> bool:
        return len(self.songs) == 0


# ─── Bot ─────────────────────────────────────────────────────────────────────
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)
        self.queues: dict[int, GuildQueue] = {}

    def get_queue(self, guild_id: int, text_channel: discord.TextChannel) -> GuildQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = GuildQueue(text_channel)
        return self.queues[guild_id]

    async def play_next(self, guild_id: int):
        queue = self.queues.get(guild_id)
        if not queue or queue.is_empty():
            async def idle_disconnect():
                await asyncio.sleep(30)
                q = self.queues.get(guild_id)
                if q and q.is_empty() and q.voice_client:
                    try:
                        await q.voice_client.disconnect()
                    except Exception:
                        pass
                    self.queues.pop(guild_id, None)
                    print(f"🔌 Disconnected from guild {guild_id} (idle).")

            task = asyncio.create_task(idle_disconnect())
            queue._idle_task = task
            return

        song = queue.songs[0]
        vc = queue.voice_client
        if not vc or not vc.is_connected():
            return

        try:
            source = discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTS)
            source = discord.PCMVolumeTransformer(source, volume=queue.volume)
            queue.current_volume_source = source
            queue.current_song = song

            def after_play(err):
                if err:
                    print(f"Player error: {err}")
                queue.current_volume_source = None
                asyncio.run_coroutine_threadsafe(
                    self._after_played(guild_id, err), self.loop
                )

            vc.play(source, after=after_play)
            await queue.text_channel.send(
                f"▶️ **Now playing:** `{song.title}` [{song.duration}]"
            )
        except Exception as e:
            print(f"Stream error: {e}")
            await queue.text_channel.send(
                f"⚠️ Skipping `{song.title}` — stream error: {e}"
            )
            queue.songs.pop(0)
            await self.play_next(guild_id)

    async def _after_played(self, guild_id: int, err: Optional[Exception]):
        queue = self.queues.get(guild_id)
        if not queue:
            return
        if not queue.is_empty():
            queue.songs.pop(0)
        if err and queue.text_channel:
            try:
                await queue.text_channel.send("⚠️ Player error, skipping to next song.")
            except Exception:
                pass
        await self.play_next(guild_id)


bot = MusicBot()
