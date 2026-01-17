"""
Neon Pi - Configuration Module
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Google Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    
    # ElevenLabs
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", alias="ELEVENLABS_VOICE_ID")
    
    # Spotify
    spotify_client_id: str = Field(default="", alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(default="", alias="SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri: str = Field(
        default="http://localhost:8000/callback/spotify",
        alias="SPOTIFY_REDIRECT_URI"
    )
    
    # Weather
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    
    # Audio
    audio_input_device: str = Field(default="default", alias="AUDIO_INPUT_DEVICE")
    audio_output_device: str = Field(default="default", alias="AUDIO_OUTPUT_DEVICE")
    
    # Paths
    base_dir: str = Field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
