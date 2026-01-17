"""
Son of Anton - YouTube Music Integration
Uses ytmusicapi for music control when Spotify is unavailable.
"""
import asyncio
import os
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from ytmusicapi import YTMusic
    YTMUSIC_AVAILABLE = True
except ImportError:
    YTMUSIC_AVAILABLE = False
    YTMusic = None

from .config import settings


class YouTubeMusicClient:
    """YouTube Music client for music control."""
    
    def __init__(self):
        self.ytmusic: Optional[YTMusic] = None
        self._authenticated = False
        self._current_video_id: Optional[str] = None
        self._auth_file = Path(settings.base_dir) / "credentials" / "ytmusic_auth.json"
    
    def is_available(self) -> bool:
        """Check if ytmusicapi is installed."""
        return YTMUSIC_AVAILABLE
    
    def is_authenticated(self) -> bool:
        """Check if authenticated with YouTube Music."""
        return self._authenticated and self.ytmusic is not None
    
    def load_auth(self) -> bool:
        """Try to load existing authentication."""
        if not YTMUSIC_AVAILABLE:
            print("[YTMusic] ytmusicapi not installed")
            return False
        
        try:
            if self._auth_file.exists():
                self.ytmusic = YTMusic(str(self._auth_file))
                self._authenticated = True
                print("[YTMusic] Loaded existing authentication")
                return True
            else:
                # Try unauthenticated mode (limited features)
                self.ytmusic = YTMusic()
                print("[YTMusic] Running in unauthenticated mode (limited features)")
                return True
        except Exception as e:
            print(f"[YTMusic] Auth load error: {e}")
            return False
    
    def get_auth_instructions(self) -> str:
        """Get instructions for authenticating YouTube Music."""
        return """
To authenticate YouTube Music:

1. On your Raspberry Pi, run:
   python3 -c "from ytmusicapi import YTMusic; YTMusic.setup(filepath='credentials/ytmusic_auth.json')"

2. Follow the browser instructions to log in with your Google account

3. Restart Son of Anton

Or run in unauthenticated mode (can search and get info, but can't control playback)
"""
    
    # ==================== Search ====================
    
    async def search(self, query: str, filter_type: str = "songs") -> list:
        """
        Search YouTube Music.
        
        Args:
            query: Search query
            filter_type: songs, videos, albums, artists, playlists
        """
        if not self.ytmusic:
            return []
        
        try:
            results = self.ytmusic.search(query, filter=filter_type, limit=5)
            return results
        except Exception as e:
            print(f"[YTMusic] Search error: {e}")
            return []
    
    async def get_song_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Get info about a song."""
        results = await self.search(query, "songs")
        if results:
            song = results[0]
            return {
                "title": song.get("title", "Unknown"),
                "artist": song.get("artists", [{}])[0].get("name", "Unknown"),
                "album": song.get("album", {}).get("name", ""),
                "video_id": song.get("videoId"),
                "thumbnail": song.get("thumbnails", [{}])[-1].get("url") if song.get("thumbnails") else None,
                "duration": song.get("duration", "0:00")
            }
        return None
    
    # ==================== Playback Control ====================
    # Note: YouTube Music doesn't have direct playback control API
    # These return URLs/info that the frontend can use
    
    async def play(self, query: str) -> Dict[str, Any]:
        """
        Find a song and return playback info.
        Returns video ID and info for frontend to handle.
        """
        if not self.ytmusic:
            return {"error": "YouTube Music not connected"}
        
        try:
            song_info = await self.get_song_info(query)
            if song_info:
                self._current_video_id = song_info.get("video_id")
                return {
                    "success": True,
                    "message": f"Found: {song_info['title']} by {song_info['artist']}",
                    "video_id": song_info.get("video_id"),
                    "title": song_info.get("title"),
                    "artist": song_info.get("artist"),
                    "thumbnail": song_info.get("thumbnail"),
                    "youtube_url": f"https://music.youtube.com/watch?v={song_info.get('video_id')}"
                }
            else:
                return {"error": f"Couldn't find: {query}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_playlist(self, query: str) -> Dict[str, Any]:
        """Search for a playlist and return its info."""
        if not self.ytmusic:
            return {"error": "YouTube Music not connected"}
        
        try:
            results = await self.search(query, "playlists")
            if results:
                playlist = results[0]
                playlist_id = playlist.get("browseId")
                
                # Get playlist details
                details = self.ytmusic.get_playlist(playlist_id, limit=10)
                
                tracks = []
                for track in details.get("tracks", [])[:5]:
                    tracks.append({
                        "title": track.get("title"),
                        "artist": track.get("artists", [{}])[0].get("name", "Unknown")
                    })
                
                return {
                    "success": True,
                    "name": details.get("title"),
                    "track_count": details.get("trackCount", 0),
                    "tracks": tracks,
                    "playlist_id": playlist_id
                }
            return {"error": f"Playlist not found: {query}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_now_playing(self) -> Optional[Dict[str, Any]]:
        """
        Get current playback info.
        Note: YTMusic API doesn't support this directly.
        Returns last played info if available.
        """
        if self._current_video_id:
            try:
                song = self.ytmusic.get_song(self._current_video_id)
                if song:
                    details = song.get("videoDetails", {})
                    return {
                        "is_playing": True,
                        "track_name": details.get("title", "Unknown"),
                        "artist_name": details.get("author", "Unknown"),
                        "image_url": details.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url"),
                        "duration_ms": int(details.get("lengthSeconds", 0)) * 1000,
                        "progress_ms": 0,
                        "source": "youtube_music"
                    }
            except:
                pass
        return None


# Global instance
youtube_music_client = YouTubeMusicClient()
