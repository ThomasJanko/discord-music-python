"""Slash command: /play"""
import discord
from discord import app_commands

from bot_core import bot, get_stream_url, is_youtube_url
from bot_core import Song


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
