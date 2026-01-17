"""
Son of Anton - Tool Executor
Handles execution of Gemini function calls.
"""
import httpx
from datetime import datetime
import pytz
from typing import Dict, Any

from .music_manager import music_manager
from .config import settings


class ToolExecutor:
    """Executes tool calls from Gemini AI."""
    
    def __init__(self):
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute a tool call and return the result.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool
            
        Returns:
            Result string to send back to Gemini
        """
        print(f"[Tools] Executing: {tool_name}({args})")
        
        try:
            # Music tools (uses Spotify or YouTube Music automatically)
            if tool_name == "play_music" or tool_name == "spotify_play":
                query = args.get("query")
                content_type = args.get("type", "track")
                return await music_manager.play(query, content_type)
            
            elif tool_name == "pause_music" or tool_name == "spotify_pause":
                return await music_manager.pause()
            
            elif tool_name == "resume_music" or tool_name == "spotify_resume":
                return await music_manager.resume()
            
            elif tool_name == "skip_track" or tool_name == "spotify_skip":
                return await music_manager.skip()
            
            elif tool_name == "previous_track" or tool_name == "spotify_previous":
                return await music_manager.previous()
            
            elif tool_name == "set_volume" or tool_name == "spotify_volume":
                volume = args.get("volume", 50)
                return await music_manager.set_volume(volume)
            
            elif tool_name == "now_playing" or tool_name == "spotify_now_playing":
                now = await music_manager.get_now_playing()
                if now:
                    source = now.get("source", "music service")
                    if now.get("is_podcast"):
                        return f"Currently playing podcast: {now['episode_name']} from {now['show_name']} (on {source})"
                    else:
                        return f"Currently playing: {now['track_name']} by {now['artist_name']} (on {source})"
                return "Nothing is currently playing."
            
            elif tool_name == "search_music":
                query = args.get("query", "")
                return await music_manager.search(query)
            
            # Weather tool
            elif tool_name == "get_weather":
                location = args.get("location", "New York")
                return await self._get_weather(location)
            
            # Time tool
            elif tool_name == "get_current_time":
                timezone = args.get("timezone", "America/Toronto")
                return self._get_time(timezone)
            
            # Web fetch tool
            elif tool_name == "fetch_web_content":
                url = args.get("url", "")
                return await self._fetch_web_content(url)
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            print(f"[Tools] Error executing {tool_name}: {e}")
            return f"Error executing tool: {e}"
    
    async def _get_weather(self, location: str) -> str:
        """Get weather using OpenWeather API."""
        if not settings.openweather_api_key:
            return "Weather service not configured. Add OPENWEATHER_API_KEY to .env"
        
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": settings.openweather_api_key,
                "units": "imperial"  # Fahrenheit
            }
            
            response = await self._http_client.get(url, params=params)
            data = response.json()
            
            if response.status_code == 200:
                temp = round(data["main"]["temp"])
                feels_like = round(data["main"]["feels_like"])
                desc = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]
                
                return (
                    f"Weather in {location}: {temp}°F (feels like {feels_like}°F), "
                    f"{desc}, {humidity}% humidity"
                )
            else:
                return f"Couldn't get weather for {location}"
                
        except Exception as e:
            return f"Weather error: {e}"
    
    def _get_time(self, timezone: str) -> str:
        """Get current time in specified timezone."""
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return now.strftime("It's %I:%M %p on %A, %B %d, %Y")
        except Exception:
            now = datetime.now()
            return now.strftime("It's %I:%M %p on %A, %B %d, %Y")
    
    async def _fetch_web_content(self, url: str) -> str:
        """Fetch and summarize web content."""
        try:
            response = await self._http_client.get(url, follow_redirects=True)
            
            if response.status_code == 200:
                # Get text content, limit length
                content = response.text[:5000]
                
                # Basic HTML stripping
                import re
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                content = re.sub(r'<[^>]+>', ' ', content)
                content = re.sub(r'\s+', ' ', content).strip()
                
                return f"Content from {url}: {content[:2000]}..."
            else:
                return f"Failed to fetch {url}: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error fetching URL: {e}"
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()


# Global instance
tool_executor = ToolExecutor()
