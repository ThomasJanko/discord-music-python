"""Slash command: /pause"""
import discord

from bot_core import bot, MSG_NOTHING_PLAYING


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
