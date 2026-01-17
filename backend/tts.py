"""
Neon Pi - ElevenLabs Text-to-Speech
Handles voice synthesis for natural speech output.
"""
import asyncio
import io
import platform
from elevenlabs import ElevenLabs, Voice, VoiceSettings
from .config import settings


class TTSEngine:
    """ElevenLabs Text-to-Speech engine."""
    
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        self.voice_id = settings.elevenlabs_voice_id
        self._audio_queue = asyncio.Queue()
        self._is_speaking = False
    
    async def speak(self, text: str) -> bytes:
        """
        Generate speech audio from text.
        
        Args:
            text: The text to synthesize
            
        Returns:
            Audio bytes in MP3 format
        """
        try:
            print(f"[TTS] Generating speech for: {text[:50]}...")
            
            # Generate audio using ElevenLabs
            audio = self.client.generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.5,
                        similarity_boost=0.75,
                        style=0.0,
                        use_speaker_boost=True
                    )
                ),
                model="eleven_turbo_v2"  # Fast model for low latency
            )
            
            # Collect audio bytes
            audio_bytes = b""
            for chunk in audio:
                audio_bytes += chunk
            
            print(f"[TTS] Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
            
        except Exception as e:
            print(f"[TTS] Error generating speech: {e}")
            return b""
    
    async def speak_stream(self, text: str):
        """
        Stream speech audio as it's generated.
        Yields audio chunks for real-time playback.
        """
        try:
            print(f"[TTS] Streaming speech for: {text[:50]}...")
            
            audio_stream = self.client.generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.5,
                        similarity_boost=0.75
                    )
                ),
                model="eleven_turbo_v2",
                stream=True
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            print(f"[TTS] Streaming error: {e}")
    
    def list_voices(self):
        """List available voices from ElevenLabs."""
        try:
            voices = self.client.voices.get_all()
            return [
                {"id": v.voice_id, "name": v.name}
                for v in voices.voices
            ]
        except Exception as e:
            print(f"[TTS] Error listing voices: {e}")
            return []


# Global instance
tts_engine = TTSEngine()
