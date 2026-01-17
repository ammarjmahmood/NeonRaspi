"""
Son of Anton - ElevenLabs Text-to-Speech
Handles voice synthesis for natural speech output.
"""
import asyncio
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from .config import settings


class TTSEngine:
    """ElevenLabs Text-to-Speech engine."""
    
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        self.voice_id = settings.elevenlabs_voice_id
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
            audio_iterator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True
                )
            )
            
            # Collect audio bytes
            audio_bytes = b""
            for chunk in audio_iterator:
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
            
            audio_stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75
                )
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            print(f"[TTS] Streaming error: {e}")
    
    def list_voices(self):
        """List available voices from ElevenLabs."""
        try:
            response = self.client.voices.get_all()
            return [
                {"id": v.voice_id, "name": v.name}
                for v in response.voices
            ]
        except Exception as e:
            print(f"[TTS] Error listing voices: {e}")
            return []


# Global instance
tts_engine = TTSEngine()
