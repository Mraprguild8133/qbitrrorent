import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from config import config
from qbit_manager import qbit_manager
from utils import (
    format_size, format_speed, format_eta, 
    format_progress_bar, validate_magnet_link, get_state_emoji
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User sessions for tracking
user_torrents: Dict[int, Dict] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🎯 **Welcome {user.first_name}!**

I'm a **qBittorrent Telegram Bot** that can help you download torrents via magnet links.

**Commands:**
🔗 `/add` - Add a magnet link
📋 `/list` - Show all active torrents
ℹ️ `/info` - Get info about a torrent
⏸️ `/pause` - Pause a torrent
▶️ `/resume` - Resume a torrent
🗑️ `/delete` - Delete a torrent
📊 `/stats` - Show qBittorrent stats
❓ `/help` - Show this help message

**How to use:**
Simply send me a magnet link, and I'll start downloading it!
    """
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /help is issued."""
    help_text = """
📚 **Detailed Help**

**Adding torrents:**
• Send any magnet link directly in chat
• Or use `/add <magnet_link>`

**Managing torrents:**
• `/list` - See all your torrents with progress
• `/info <hash>` - Detailed info about specific torrent
• `/pause <hash>` - Pause downloading
• `/resume <hash>` - Resume downloading
• `/delete <hash>` - Remove torrent (add `--files` to delete files too)

**Examples:**
