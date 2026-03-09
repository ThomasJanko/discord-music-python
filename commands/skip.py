"""Slash command: /skip"""
import discord

from bot_core import bot, MSG_NOTHING_PLAYING


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
