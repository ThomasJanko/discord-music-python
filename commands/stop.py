"""Slash command: /stop"""
import discord

from bot_core import bot, MSG_NOTHING_PLAYING


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
