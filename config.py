import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_API_ID: str = os.getenv("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    
    # qBittorrent Configuration
    QBITTORRENT_HOST: str = os.getenv("QBITTORRENT_HOST", "http://localhost:8080")
    QBITTORRENT_USERNAME: str = os.getenv("QBITTORRENT_USERNAME", "admin")
    QBITTORRENT_PASSWORD: str = os.getenv("QBITTORRENT_PASSWORD", "adminadmin")
    
    # Bot Configuration
    ALLOWED_USERS: list = os.getenv("ALLOWED_USERS", "").split(",")
    DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "/downloads")
    MAX_TORRENTS_PER_USER: int = int(os.getenv("MAX_TORRENTS_PER_USER", "5"))
    
    # Admin Configuration
    ADMIN_IDS: list = os.getenv("ADMIN_IDS", "").split(",")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.QBITTORRENT_HOST:
            raise ValueError("QBITTORRENT_HOST is required")
        return True

config = Config()
