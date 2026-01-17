"""
Neon Pi - Spotify Integration
Handles Spotify Web API for music control and now playing.
"""
import asyncio
import time
from typing import Optional, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .config import settings


class SpotifyClient:
    """Spotify Web API client for music control."""
    
    SCOPES = [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "user-library-read",
    ]
    
    def __init__(self):
        self.sp: Optional[spotipy.Spotify] = None
        self._token_info: Optional[Dict] = None
        self._last_now_playing: Optional[Dict] = None
        self._oauth: Optional[SpotifyOAuth] = None
    
    def get_auth_url(self) -> str:
        """Get the Spotify authorization URL."""
        self._oauth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.spotify_redirect_uri,
            scope=" ".join(self.SCOPES),
            cache_path=".spotify_cache"
        )
        return self._oauth.get_authorize_url()
    
    def authenticate_with_code(self, code: str) -> bool:
        """Complete authentication with the authorization code."""
        try:
            if not self._oauth:
                self._oauth = SpotifyOAuth(
                    client_id=settings.spotify_client_id,
                    client_secret=settings.spotify_client_secret,
                    redirect_uri=settings.spotify_redirect_uri,
                    scope=" ".join(self.SCOPES),
                    cache_path=".spotify_cache"
                )
            
            self._token_info = self._oauth.get_access_token(code)
            self.sp = spotipy.Spotify(auth=self._token_info['access_token'])
            print("[Spotify] Successfully authenticated!")
            return True
        except Exception as e:
            print(f"[Spotify] Authentication error: {e}")
            return False
    
    def load_cached_token(self) -> bool:
        """Try to load a cached token."""
        try:
            self._oauth = SpotifyOAuth(
                client_id=settings.spotify_client_id,
                client_secret=settings.spotify_client_secret,
                redirect_uri=settings.spotify_redirect_uri,
                scope=" ".join(self.SCOPES),
                cache_path=".spotify_cache"
            )
            
            token_info = self._oauth.get_cached_token()
            if token_info:
                self._token_info = token_info
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                print("[Spotify] Loaded cached token")
                return True
            return False
        except Exception as e:
            print(f"[Spotify] Error loading cached token: {e}")
            return False
    
    def _ensure_token(self):
        """Ensure we have a valid token, refreshing if needed."""
        if not self._oauth or not self._token_info:
            return False
        
        if self._oauth.is_token_expired(self._token_info):
            print("[Spotify] Refreshing expired token...")
            self._token_info = self._oauth.refresh_access_token(
                self._token_info['refresh_token']
            )
            self.sp = spotipy.Spotify(auth=self._token_info['access_token'])
        
        return True
    
    def is_authenticated(self) -> bool:
        """Check if we're authenticated with Spotify."""
        return self.sp is not None
    
    # ==================== Playback Control ====================
    
    async def play(self, query: str = None, content_type: str = "track") -> str:
        """Play music on Spotify."""
        if not self._ensure_token():
            return "Not connected to Spotify. Please authenticate first."
        
        try:
            if query:
                # Search for the content
                results = self.sp.search(q=query, type=content_type, limit=1)
                
                key = f"{content_type}s"
                if results[key]['items']:
                    item = results[key]['items'][0]
                    uri = item['uri']
                    name = item['name']
                    
                    if content_type == "track":
                        self.sp.start_playback(uris=[uri])
                    else:
                        self.sp.start_playback(context_uri=uri)
                    
                    return f"Now playing: {name}"
                else:
                    return f"Couldn't find {content_type}: {query}"
            else:
                # Just resume playback
                self.sp.start_playback()
                return "Resuming playback"
                
        except spotipy.SpotifyException as e:
            if "NO_ACTIVE_DEVICE" in str(e):
                return "No active Spotify device found. Please open Spotify on a device."
            return f"Spotify error: {e}"
        except Exception as e:
            return f"Error playing: {e}"
    
    async def pause(self) -> str:
        """Pause playback."""
        if not self._ensure_token():
            return "Not connected to Spotify."
        
        try:
            self.sp.pause_playback()
            return "Paused"
        except Exception as e:
            return f"Error pausing: {e}"
    
    async def resume(self) -> str:
        """Resume playback."""
        if not self._ensure_token():
            return "Not connected to Spotify."
        
        try:
            self.sp.start_playback()
            return "Resumed"
        except Exception as e:
            return f"Error resuming: {e}"
    
    async def skip(self) -> str:
        """Skip to next track."""
        if not self._ensure_token():
            return "Not connected to Spotify."
        
        try:
            self.sp.next_track()
            await asyncio.sleep(0.5)  # Wait for track change
            now = await self.get_now_playing()
            if now and now.get('track_name'):
                return f"Skipped to: {now['track_name']}"
            return "Skipped to next track"
        except Exception as e:
            return f"Error skipping: {e}"
    
    async def previous(self) -> str:
        """Go to previous track."""
        if not self._ensure_token():
            return "Not connected to Spotify."
        
        try:
            self.sp.previous_track()
            await asyncio.sleep(0.5)
            now = await self.get_now_playing()
            if now and now.get('track_name'):
                return f"Playing: {now['track_name']}"
            return "Playing previous track"
        except Exception as e:
            return f"Error: {e}"
    
    async def set_volume(self, volume: int) -> str:
        """Set playback volume (0-100)."""
        if not self._ensure_token():
            return "Not connected to Spotify."
        
        try:
            volume = max(0, min(100, volume))
            self.sp.volume(volume)
            return f"Volume set to {volume}%"
        except Exception as e:
            return f"Error setting volume: {e}"
    
    # ==================== Now Playing ====================
    
    async def get_now_playing(self) -> Optional[Dict[str, Any]]:
        """Get current playback information."""
        if not self._ensure_token():
            return None
        
        try:
            playback = self.sp.current_playback()
            
            if not playback or not playback.get('item'):
                return None
            
            item = playback['item']
            is_podcast = item.get('type') == 'episode'
            
            data = {
                "is_playing": playback.get('is_playing', False),
                "progress_ms": playback.get('progress_ms', 0),
                "duration_ms": item.get('duration_ms', 0),
                "is_podcast": is_podcast,
            }
            
            if is_podcast:
                data.update({
                    "episode_name": item.get('name', 'Unknown Episode'),
                    "show_name": item.get('show', {}).get('name', 'Unknown Show'),
                    "image_url": item.get('images', [{}])[0].get('url') if item.get('images') else None,
                    "description": item.get('description', ''),
                })
            else:
                data.update({
                    "track_name": item.get('name', 'Unknown Track'),
                    "artist_name": ", ".join(a['name'] for a in item.get('artists', [])),
                    "album_name": item.get('album', {}).get('name', 'Unknown Album'),
                    "image_url": item.get('album', {}).get('images', [{}])[0].get('url'),
                })
            
            self._last_now_playing = data
            return data
            
        except Exception as e:
            print(f"[Spotify] Error getting now playing: {e}")
            return self._last_now_playing
    
    async def get_lyrics(self) -> Optional[str]:
        """
        Get lyrics for current track.
        Note: Spotify's lyrics API requires special access.
        This is a placeholder for integration with Musixmatch or similar.
        """
        # TODO: Integrate with Musixmatch API or Genius
        return None


# Global instance
spotify_client = SpotifyClient()
