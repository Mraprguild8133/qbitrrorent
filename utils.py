import re
import humanize
from datetime import datetime, timedelta
from typing import Optional

def format_size(bytes_size: int) -> str:
    """Convert bytes to human readable format"""
    return humanize.naturalsize(bytes_size, binary=True)

def format_speed(speed_bytes: int) -> str:
    """Format download/upload speed"""
    return f"{humanize.naturalsize(speed_bytes, binary=True)}/s"

def format_eta(eta_seconds: int) -> str:
    """Format ETA to human readable"""
    if eta_seconds < 0 or eta_seconds == 8640000:
        return "Unknown"
    return str(timedelta(seconds=eta_seconds))

def format_progress_bar(progress: float, length: int = 20) -> str:
    """Create a progress bar"""
    filled = int(length * progress / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"`[{bar}]`"

def validate_magnet_link(text: str) -> Optional[str]:
    """Validate if text is a magnet link"""
    magnet_pattern = r'magnet:\?xt=urn:btih:[a-zA-Z0-9]+'
    if re.match(magnet_pattern, text):
        return text
    return None

def get_state_emoji(state: str) -> str:
    """Get emoji for torrent state"""
    state_emoji = {
        'downloading': '⬇️',
        'uploading': '⬆️',
        'pausedDL': '⏸️',
        'pausedUP': '⏸️',
        'queuedDL': '⏳',
        'queuedUP': '⏳',
        'stalledDL': '⚠️',
        'stalledUP': '⚠️',
        'checkingUP': '🔍',
        'checkingDL': '🔍',
        'error': '❌',
        'missingFiles': '📁❌',
        'unknown': '❓'
    }
    return state_emoji.get(state, '🔁')
