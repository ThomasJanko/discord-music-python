"""Slash command: /queue"""
import discord

from bot_core import bot


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
