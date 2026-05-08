import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from qbittorrentapi import Client, LoginFailed, APIConnectionError
from config import config

logger = logging.getLogger(__name__)

class QBitManager:
    def __init__(self):
        self.client = None
        self.connected = False
        self._reconnect_attempts = 0
        
    async def connect(self) -> bool:
        """Establish connection to qBittorrent"""
        try:
            self.client = Client(
                host=config.QBITTORRENT_HOST,
                username=config.QBITTORRENT_USERNAME,
                password=config.QBITTORRENT_PASSWORD,
                VERIFY_WARNINGS=False
            )
            
            # Test connection
            await asyncio.to_thread(self.client.auth_log_in)
            self.connected = True
            self._reconnect_attempts = 0
            logger.info(f"Connected to qBittorrent at {config.QBITTORRENT_HOST}")
            return True
            
        except LoginFailed as e:
            logger.error(f"Login failed: {e}")
            self.connected = False
            return False
        except APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            self.connected = False
            return False
    
    async def add_magnet(self, magnet_link: str, category: str = "telegram") -> Optional[Dict]:
        """Add magnet link to qBittorrent"""
        if not self.connected:
            await self.connect()
            
        try:
            result = await asyncio.to_thread(
                self.client.torrents_add,
                urls=magnet_link,
                save_path=config.DOWNLOAD_PATH,
                category=category,
                is_paused=False
            )
            
            if result == "Ok.":
                # Get added torrent info
                torrents = await self.get_torrents()
                for torrent in torrents:
                    if torrent.get('magnet_uri') == magnet_link:
                        return torrent
            return None
            
        except Exception as e:
            logger.error(f"Failed to add magnet: {e}")
            return None
    
    async def get_torrents(self, filter_type: str = "all") -> List[Dict]:
        """Get list of torrents"""
        if not self.connected:
            await self.connect()
            
        try:
            torrents = await asyncio.to_thread(
                self.client.torrents_info,
                status_filter=filter_type
            )
            return [self._format_torrent_info(t) for t in torrents]
        except Exception as e:
            logger.error(f"Failed to get torrents: {e}")
            return []
    
    async def pause_torrent(self, torrent_hash: str) -> bool:
        """Pause a torrent"""
        if not self.connected:
            await self.connect()
            
        try:
            await asyncio.to_thread(self.client.torrents_pause, torrent_hashes=torrent_hash)
            return True
        except Exception as e:
            logger.error(f"Failed to pause torrent: {e}")
            return False
    
    async def resume_torrent(self, torrent_hash: str) -> bool:
        """Resume a torrent"""
        if not self.connected:
            await self.connect()
            
        try:
            await asyncio.to_thread(self.client.torrents_resume, torrent_hashes=torrent_hash)
            return True
        except Exception as e:
            logger.error(f"Failed to resume torrent: {e}")
            return False
    
    async def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """Delete a torrent"""
        if not self.connected:
            await self.connect()
            
        try:
            await asyncio.to_thread(
                self.client.torrents_delete,
                torrent_hashes=torrent_hash,
                delete_files=delete_files
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete torrent: {e}")
            return False
    
    async def get_torrent_info(self, torrent_hash: str) -> Optional[Dict]:
        """Get detailed information about a specific torrent"""
        if not self.connected:
            await self.connect()
            
        try:
            torrents = await asyncio.to_thread(
                self.client.torrents_info,
                torrent_hashes=torrent_hash
            )
            if torrents:
                return self._format_torrent_info(torrents[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get torrent info: {e}")
            return None
    
    def _format_torrent_info(self, torrent) -> Dict:
        """Format torrent information for display"""
        return {
            'hash': torrent.get('hash', ''),
            'name': torrent.get('name', 'Unknown'),
            'size': torrent.get('size', 0),
            'progress': torrent.get('progress', 0) * 100,
            'state': torrent.get('state', 'unknown'),
            'download_speed': torrent.get('dlspeed', 0),
            'upload_speed': torrent.get('upspeed', 0),
            'num_seeds': torrent.get('num_seeds', 0),
            'num_leechs': torrent.get('num_leechs', 0),
            'eta': torrent.get('eta', 0),
            'added_on': torrent.get('added_on', 0),
            'category': torrent.get('category', ''),
        }

# Singleton instance
qbit_manager = QBitManager()
