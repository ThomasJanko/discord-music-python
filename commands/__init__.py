"""Load all command modules so they register with the bot tree."""
from . import (
    play,
    skip,
    stop,
    queue,
    pause,
    resume,
    nowplaying,
    volume,
)

__all__ = ["play", "skip", "stop", "queue", "pause", "resume", "nowplaying", "volume"]
