"""
Son of Anton - Music Service Manager
Handles switching between Spotify and YouTube Music.
"""
from typing import Optional, Dict, Any
from .spotify_client import spotify_client
from .youtube_music_client import youtube_music_client


class MusicManager:
    """
    Unified music service manager.
    Uses Spotify when available, falls back to YouTube Music.
    """
    
    def __init__(self):
        self._preferred_service = "spotify"  # or "youtube_music"
    
    @property
    def active_service(self) -> str:
        """Get the currently active music service."""
        if spotify_client.is_authenticated():
            return "spotify"
        elif youtube_music_client.is_authenticated():
            return "youtube_music"
        else:
            return "none"
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all music services."""
        return {
            "spotify": {
                "connected": spotify_client.is_authenticated(),
                "available": True
            },
            "youtube_music": {
                "connected": youtube_music_client.is_authenticated(),
                "available": youtube_music_client.is_available()
            },
            "active": self.active_service
        }
    
    async def play(self, query: str, content_type: str = "track") -> str:
        """Play music using the active service."""
        if spotify_client.is_authenticated():
            return await spotify_client.play(query, content_type)
        elif youtube_music_client.is_authenticated() or youtube_music_client.is_available():
            result = await youtube_music_client.play(query)
            if result.get("success"):
                return result.get("message", "Playing...")
            return result.get("error", "Couldn't play that")
        else:
            return "No music service connected. Connect Spotify or YouTube Music first."
    
    async def pause(self) -> str:
        """Pause playback."""
        if spotify_client.is_authenticated():
            return await spotify_client.pause()
        else:
            return "Pause not available for YouTube Music (use your device)"
    
    async def resume(self) -> str:
        """Resume playback."""
        if spotify_client.is_authenticated():
            return await spotify_client.resume()
        else:
            return "Resume not available for YouTube Music (use your device)"
    
    async def skip(self) -> str:
        """Skip to next track."""
        if spotify_client.is_authenticated():
            return await spotify_client.skip()
        else:
            return "Skip not available for YouTube Music (use your device)"
    
    async def previous(self) -> str:
        """Go to previous track."""
        if spotify_client.is_authenticated():
            return await spotify_client.previous()
        else:
            return "Previous not available for YouTube Music (use your device)"
    
    async def set_volume(self, volume: int) -> str:
        """Set volume."""
        if spotify_client.is_authenticated():
            return await spotify_client.set_volume(volume)
        else:
            return "Volume control not available for YouTube Music"
    
    async def get_now_playing(self) -> Optional[Dict[str, Any]]:
        """Get current playback info."""
        if spotify_client.is_authenticated():
            data = await spotify_client.get_now_playing()
            if data:
                data["source"] = "spotify"
            return data
        elif youtube_music_client.is_authenticated():
            return await youtube_music_client.get_now_playing()
        return None
    
    async def search(self, query: str) -> str:
        """Search for music and describe results."""
        if youtube_music_client.is_available():
            info = await youtube_music_client.get_song_info(query)
            if info:
                return f"Found '{info['title']}' by {info['artist']}"
        return f"Couldn't find: {query}"


# Global instance
music_manager = MusicManager()
