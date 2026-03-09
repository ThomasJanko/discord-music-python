"""Slash command: /nowplaying"""
import discord

from bot_core import bot, MSG_NOTHING_PLAYING


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
