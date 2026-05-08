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

**Status indicators:**
⬇️ Downloading | ⬆️ Uploading | ⏸️ Paused
⏳ Queued | ⚠️ Stalled | ❌ Error
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def add_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a magnet link to qBittorrent"""
    user_id = update.effective_user.id
    
    # Check if user is allowed
    if config.ALLOWED_USERS and str(user_id) not in config.ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    # Get magnet link from command or replied message
    magnet_link = None
    if context.args:
        magnet_link = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        magnet_link = update.message.reply_to_message.text
    
    if not magnet_link:
        await update.message.reply_text(
            "❌ Please provide a magnet link!\n\n"
            "Usage: `/add <magnet_link>`\n"
            "Or reply to a message containing a magnet link.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Validate magnet link
    if not validate_magnet_link(magnet_link):
        await update.message.reply_text("❌ Invalid magnet link! Please check and try again.")
        return
    
    # Send processing message
    msg = await update.message.reply_text(
        "🔄 **Adding magnet link to qBittorrent...**",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Add to qBittorrent
    result = await qbit_manager.add_magnet(magnet_link)
    
    if result:
        await msg.edit_text(
            f"✅ **Torrent added successfully!**\n\n"
            f"📛 **Name:** `{result.get('name')}`\n"
            f"💾 **Size:** {format_size(result.get('size'))}\n"
            f"🔗 **Hash:** `{result.get('hash')[:16]}...`\n\n"
            f"Use `/list` to track progress.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await msg.edit_text(
            "❌ **Failed to add magnet link!**\n\n"
            "Possible reasons:\n"
            "• qBittorrent is not connected\n"
            "• Invalid magnet link\n"
            "• Torrent already exists",
            parse_mode=ParseMode.MARKDOWN
        )

async def list_torrents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active torrents"""
    await update.message.reply_chat_action("typing")
    
    torrents = await qbit_manager.get_torrents()
    
    if not torrents:
        await update.message.reply_text(
            "📭 **No active torrents found!**\n\n"
            "Send me a magnet link to start downloading.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Group torrents by user (simplified - in production use proper user tracking)
    active_torrents = [t for t in torrents if t.get('progress', 0) < 100]
    completed_torrents = [t for t in torrents if t.get('progress', 0) >= 100]
    
    message = "📋 **Torrent List**\n\n"
    
    if active_torrents:
        message += "**⬇️ Active Downloads:**\n"
        for i, torrent in enumerate(active_torrents[:10], 1):
            progress = torrent.get('progress', 0)
            speed = torrent.get('download_speed', 0)
            eta = torrent.get('eta', 0)
            state_emoji = get_state_emoji(torrent.get('state', 'unknown'))
            
            message += f"\n{i}. {state_emoji} `{torrent.get('hash')[:8]}...`\n"
            message += f"   📛 `{torrent.get('name')[:40]}`\n"
            message += f"   📊 {format_progress_bar(progress)}\n"
            message += f"   💾 {progress:.1f}% | {format_speed(speed)}"
            if eta > 0:
                message += f" | ⏱️ {format_eta(eta)}"
            message += "\n"
    
    if completed_torrents and len(completed_torrents) <= 20:
        message += f"\n**✅ Completed ({len(completed_torrents)}):**\n"
        for torrent in completed_torrents[:5]:
            message += f"• `{torrent.get('name')[:50]}`\n"
    
    if len(torrents) > 15:
        message += f"\n_Showing {len(active_torrents)}/{len(torrents)} torrents_"
    
    # Add keyboard for navigation
    keyboard = []
    if active_torrents:
        keyboard.append([
            InlineKeyboardButton("⏸️ Pause All", callback_data="pause_all"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_list")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(
        message, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def torrent_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed information about a torrent"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a torrent hash!\n\n"
            "Usage: `/info <torrent_hash>`\n"
            "Get hash from `/list` command.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    torrent_hash = context.args[0]
    torrent = await qbit_manager.get_torrent_info(torrent_hash)
    
    if not torrent:
        await update.message.reply_text("❌ Torrent not found!")
        return
    
    progress = torrent.get('progress', 0)
    state_emoji = get_state_emoji(torrent.get('state', 'unknown'))
    
    message = f"""
{state_emoji} **Torrent Details**

📛 **Name:** `{torrent.get('name')}`
🔗 **Hash:** `{torrent.get('hash')}`
💾 **Size:** {format_size(torrent.get('size'))}
📊 **Progress:** {progress:.1f}%

{format_progress_bar(progress)}

⚡ **Download Speed:** {format_speed(torrent.get('download_speed', 0))}
🔥 **Upload Speed:** {format_speed(torrent.get('upload_speed', 0))}
🌱 **Seeds:** {torrent.get('num_seeds', 0)} | 🧲 **Peers:** {torrent.get('num_leechs', 0)}

⏱️ **ETA:** {format_eta(torrent.get('eta', 0))}
📁 **Category:** {torrent.get('category', 'None')}
📅 **Added:** {datetime.fromtimestamp(torrent.get('added_on', 0)).strftime('%Y-%m-%d %H:%M')}
"""
    
    # Add control buttons
    keyboard = [
        [
            InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{torrent_hash}"),
            InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{torrent_hash}"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{torrent_hash}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"info_{torrent_hash}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def pause_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause a torrent"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a torrent hash!\n\nUsage: `/pause <torrent_hash>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    torrent_hash = context.args[0]
    success = await qbit_manager.pause_torrent(torrent_hash)
    
    if success:
        await update.message.reply_text(f"✅ Torrent `{torrent_hash[:8]}...` has been paused.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to pause torrent!")

async def resume_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume a torrent"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a torrent hash!\n\nUsage: `/resume <torrent_hash>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    torrent_hash = context.args[0]
    success = await qbit_manager.resume_torrent(torrent_hash)
    
    if success:
        await update.message.reply_text(f"✅ Torrent `{torrent_hash[:8]}...` has been resumed.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to resume torrent!")

async def delete_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a torrent"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a torrent hash!\n\nUsage: `/delete <torrent_hash> [--files]`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    torrent_hash = context.args[0]
    delete_files = "--files" in context.args
    
    success = await qbit_manager.delete_torrent(torrent_hash, delete_files)
    
    if success:
        msg = f"✅ Torrent `{torrent_hash[:8]}...` has been deleted."
        if delete_files:
            msg += "\n📁 Downloaded files have also been removed."
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to delete torrent!")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show qBittorrent statistics"""
    await update.message.reply_chat_action("typing")
    
    torrents = await qbit_manager.get_torrents()
    
    if not torrents:
        await update.message.reply_text("No torrents found!")
        return
    
    total_downloading = len([t for t in torrents if t.get('progress', 0) < 100])
    total_completed = len([t for t in torrents if t.get('progress', 0) >= 100])
    total_size = sum(t.get('size', 0) for t in torrents)
    total_download_speed = sum(t.get('download_speed', 0) for t in torrents)
    total_upload_speed = sum(t.get('upload_speed', 0) for t in torrents)
    
    message = f"""
📊 **qBittorrent Statistics**

📥 **Downloading:** {total_downloading}
✅ **Completed:** {total_completed}
📊 **Total Torrents:** {len(torrents)}

💾 **Total Size:** {format_size(total_size)}

⚡ **Total Download Speed:** {format_speed(total_download_speed)}
🔥 **Total Upload Speed:** {format_speed(total_upload_speed)}

🔌 **Connected to:** {config.QBITTORRENT_HOST}
    """
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def handle_magnet_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle magnet links sent directly in chat"""
    text = update.message.text
    
    if validate_magnet_link(text):
        # Simulate /add command
        context.args = [text]
        await add_magnet(update, context)
    else:
        await update.message.reply_text(
            "❌ I can only process magnet links!\n"
            "Use /help to see available commands."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "refresh_list":
        await list_torrents(update, context)
    
    elif data.startswith("pause_"):
        torrent_hash = data.replace("pause_", "")
        await qbit_manager.pause_torrent(torrent_hash)
        await query.edit_message_text(f"✅ Torrent paused! Use /info {torrent_hash} to see updated status.")
    
    elif data.startswith("resume_"):
        torrent_hash = data.replace("resume_", "")
        await qbit_manager.resume_torrent(torrent_hash)
        await query.edit_message_text(f"✅ Torrent resumed! Use /info {torrent_hash} to see updated status.")
    
    elif data.startswith("delete_"):
        torrent_hash = data.replace("delete_", "")
        await qbit_manager.delete_torrent(torrent_hash)
        await query.edit_message_text(f"✅ Torrent deleted!")
    
    elif data.startswith("info_"):
        torrent_hash = data.replace("info_", "")
        # Create fake update to reuse info function
        class FakeUpdate:
            effective_user = update.effective_user
            message = await update.effective_message.reply_text("Loading...")
        
        fake_context = ContextTypes.DEFAULT_TYPE()
        fake_context.args = [torrent_hash]
        await torrent_info(fake_update, fake_context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred! Please try again later."
        )

def main():
    """Start the bot"""
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Create application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_magnet))
    application.add_handler(CommandHandler("list", list_torrents))
    application.add_handler(CommandHandler("info", torrent_info))
    application.add_handler(CommandHandler("pause", pause_torrent))
    application.add_handler(CommandHandler("resume", resume_torrent))
    application.add_handler(CommandHandler("delete", delete_torrent))
    application.add_handler(CommandHandler("stats", stats))
    
    # Add message handler for magnet links
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_magnet_message))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Connect to qBittorrent
    async def init_qbit():
        await qbit_manager.connect()
    
    # Run initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_qbit())
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
