"""
Discord music bot (Python) — same features as the Node version.
Slash commands: /play, /skip, /stop, /queue, /pause, /resume, /nowplaying
"""
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
import os

load_dotenv()

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
    # Handle playlist (take first entry)
    if "entries" in info and info["entries"]:
        info = info["entries"][0]
    if not info.get("url") and not info.get("formats"):
        raise ValueError("No playable format")
    url = info.get("url")
    if not url and info.get("formats"):
        # Pick first format with url (audio)
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
            # Schedule disconnect after 30s idle
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
            queue._idle_task = task  # keep ref so task isn't garbage-collected
            return

        song = queue.songs[0]
        vc = queue.voice_client
        if not vc or not vc.is_connected():
            return

        try:
            source = discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTS)
            queue.current_song = song

            def after_play(err):
                if err:
                    print(f"Player error: {err}")
                asyncio.run_coroutine_threadsafe(
                    bot._after_played(guild_id, err), bot.loop
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


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced ({len(synced)} commands).")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# ─── /play ───────────────────────────────────────────────────────────────────
@bot.tree.command(name="play", description="Play a song by name or YouTube URL")
@app_commands.describe(query="Song name or YouTube URL")
async def play(interaction: discord.Interaction, query: str):
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.response.send_message(
            "❌ You need to be in a voice channel first!", ephemeral=True
        )
        return

    await interaction.response.defer()

    try:
        if is_youtube_url(query):
            data = await get_stream_url(query, is_search=False)
        else:
            data = await get_stream_url(query, is_search=True)
    except Exception as e:
        await interaction.edit_original_response(
            content=f"❌ Could not find **{query}**.\n`{e}`"
        )
        return

    song = Song(title=data["title"], url=data["url"], duration=data["duration"])
    guild_id = interaction.guild_id
    queue = bot.get_queue(guild_id, interaction.channel)

    # Join voice if needed
    if queue.voice_client is None or not queue.voice_client.is_connected():
        queue.voice_client = await voice_channel.connect()

    queue.songs.append(song)
    was_empty = len(queue.songs) == 1

    if was_empty:
        await bot.play_next(guild_id)
        await interaction.edit_original_response(
            content=f"🎵 **Now loading:** `{song.title}` [{song.duration}]"
        )
    else:
        await interaction.edit_original_response(
            content=f"✅ **Added to queue (#{len(queue.songs)}):** `{song.title}` [{song.duration}]"
        )


# ─── /skip ───────────────────────────────────────────────────────────────────
@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue or queue.is_empty():
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return
    queue.skip()
    await interaction.response.send_message("⏭️ **Skipped!**")


# ─── /stop ───────────────────────────────────────────────────────────────────
@bot.tree.command(name="stop", description="Stop playback and clear the queue")
async def stop(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue:
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return
    queue.songs.clear()
    queue.skip()
    if queue.voice_client and queue.voice_client.is_connected():
        await queue.voice_client.disconnect()
    bot.queues.pop(interaction.guild_id, None)
    await interaction.response.send_message("⏹️ **Stopped** and cleared the queue. Goodbye! 👋")


# ─── /queue ──────────────────────────────────────────────────────────────────
@bot.tree.command(name="queue", description="Show the current song queue")
async def queue_cmd(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue or queue.is_empty():
        await interaction.response.send_message(
            "📭 The queue is empty.", ephemeral=True
        )
        return
    lines = []
    for i, s in enumerate(queue.songs):
        prefix = "▶️" if i == 0 else f"`{i}.`"
        lines.append(f"{prefix} **{s.title}** [{s.duration}]")
    await interaction.response.send_message(
        f"**📋 Queue — {len(queue.songs)} song(s):**\n" + "\n".join(lines)
    )


# ─── /pause ──────────────────────────────────────────────────────────────────
@bot.tree.command(name="pause", description="Pause playback")
async def pause(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue or not queue.voice_client:
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return
    vc = queue.voice_client
    if vc.is_paused():
        await interaction.response.send_message("❌ Already paused.", ephemeral=True)
        return
    vc.pause()
    await interaction.response.send_message("⏸️ **Paused.**")


# ─── /resume ─────────────────────────────────────────────────────────────────
@bot.tree.command(name="resume", description="Resume playback")
async def resume(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue or not queue.voice_client:
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return
    vc = queue.voice_client
    if not vc.is_paused():
        await interaction.response.send_message("❌ Not paused.", ephemeral=True)
        return
    vc.resume()
    await interaction.response.send_message("▶️ **Resumed!**")


# ─── /nowplaying ─────────────────────────────────────────────────────────────
@bot.tree.command(name="nowplaying", description="Show the currently playing song")
async def nowplaying(interaction: discord.Interaction):
    queue = bot.queues.get(interaction.guild_id)
    if not queue or not queue.current_song:
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return
    s = queue.current_song
    await interaction.response.send_message(
        f"🎵 **Now Playing:** **{s.title}** [{s.duration}]\n🔗 {s.url}"
    )


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Missing DISCORD_TOKEN in .env")
        exit(1)
    bot.run(token)
