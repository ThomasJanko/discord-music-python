"""
Discord music bot (Python) — slash commands: /play, /skip, /stop, /queue, /pause, /resume, /nowplaying, /volume
"""
import os

from dotenv import load_dotenv

load_dotenv()

from bot_core import bot
import commands  # noqa: F401 — register slash commands


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced ({len(synced)} commands).")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Missing DISCORD_TOKEN in .env")
        exit(1)
    bot.run(token)
