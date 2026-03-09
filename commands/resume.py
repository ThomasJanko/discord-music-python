"""Slash command: /resume"""
import discord

from bot_core import bot, MSG_NOTHING_PLAYING


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
