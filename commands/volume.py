"""Slash command: /volume"""
import discord
from discord import app_commands

from bot_core import bot, MSG_NOTHING_PLAYING


@bot.tree.command(name="volume", description="Set volume from 1 to 100")
@app_commands.describe(level="Volume level (1–100)")
async def volume(interaction: discord.Interaction, level: int):
    if level < 1 or level > 100:
        await interaction.response.send_message(
            "❌ Volume must be between **1** and **100**.", ephemeral=True
        )
        return

    queue = bot.queues.get(interaction.guild_id)
    if not queue:
        await interaction.response.send_message(
            MSG_NOTHING_PLAYING, ephemeral=True
        )
        return

    # Store as 0.0–1.0 for discord.PCMVolumeTransformer
    queue.volume = level / 100.0
    if queue.current_volume_source:
        queue.current_volume_source.volume = queue.volume

    await interaction.response.send_message(f"🔊 **Volume set to {level}%**")
