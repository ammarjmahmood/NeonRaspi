"""
Neon Pi - Speech to Text
Uses Faster Whisper for efficient local transcription.
"""
import asyncio
import numpy as np
import tempfile
import wave
import os
from typing import Optional, Tuple
import threading
import queue


class SpeechToText:
    """
    Speech-to-text engine using Faster Whisper.
    Optimized for Raspberry Pi with smaller models.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize STT engine.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium)
                       - tiny: Fastest, less accurate
                       - base: Good balance for Pi 4
                       - small: Better accuracy, slower
        """
        self.model_size = model_size
        self._model = None
        self._recording = False
        self._audio_frames = []
        self._sample_rate = 16000
    
    def _load_model(self):
        """Lazy-load the Whisper model."""
        if self._model is not None:
            return
        
        try:
            from faster_whisper import WhisperModel
            
            print(f"[STT] Loading Whisper model: {self.model_size}...")
            
            # Use CPU for Pi, or CUDA if available
            self._model = WhisperModel(
                self.model_size,
                device="cpu",  # Change to "cuda" if GPU available
                compute_type="int8"  # Optimized for CPU
            )
            
            print("[STT] Model loaded successfully")
            
        except ImportError:
            print("[STT] faster-whisper not installed. Install with: pip install faster-whisper")
        except Exception as e:
            print(f"[STT] Error loading model: {e}")
    
    async def record_audio(
        self,
        duration: float = 5.0,
        silence_threshold: float = 500,
        silence_duration: float = 1.5,
        on_audio_level: Optional[callable] = None
    ) -> np.ndarray:
        """
        Record audio from microphone.
        
        Args:
            duration: Maximum recording duration in seconds
            silence_threshold: Audio level threshold for silence detection
            silence_duration: Duration of silence to stop recording
            on_audio_level: Callback for audio level updates (for visualization)
            
        Returns:
            Audio data as numpy array
        """
        try:
            import sounddevice as sd
            
            print("[STT] Recording...")
            
            frames = []
            silence_frames = 0
            max_silence_frames = int(silence_duration * self._sample_rate / 1024)
            
            def callback(indata, frame_count, time_info, status):
                nonlocal silence_frames
                
                if status:
                    print(f"[Audio] {status}")
                
                # Calculate audio level
                level = np.abs(indata).mean()
                
                if on_audio_level:
                    asyncio.create_task(on_audio_level(float(level)))
                
                # Check for silence
                if level < silence_threshold and len(frames) > self._sample_rate:
                    silence_frames += 1
                else:
                    silence_frames = 0
                
                frames.append(indata.copy())
            
            # Record with silence detection
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=1024,
                callback=callback
            ):
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    await asyncio.sleep(0.1)
                    
                    # Check for stop conditions
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    if elapsed >= duration:
                        print("[STT] Max duration reached")
                        break
                    
                    if silence_frames >= max_silence_frames and len(frames) > 10:
                        print("[STT] Silence detected, stopping")
                        break
            
            # Combine frames
            if frames:
                audio = np.concatenate(frames, axis=0).flatten()
                print(f"[STT] Recorded {len(audio) / self._sample_rate:.1f}s of audio")
                return audio
            
            return np.array([])
            
        except Exception as e:
            print(f"[STT] Recording error: {e}")
            return np.array([])
    
    async def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Transcribed text
        """
        if len(audio) == 0:
            return ""
        
        self._load_model()
        
        if self._model is None:
            return ""
        
        try:
            print("[STT] Transcribing...")
            
            # Run transcription in thread pool to not block
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self._model.transcribe(
                    audio,
                    beam_size=5,
                    language="en",
                    vad_filter=True  # Voice activity detection
                )
            )
            
            # Combine segments
            text = " ".join(segment.text for segment in segments).strip()
            
            print(f"[STT] Transcribed: {text}")
            return text
            
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return ""
    
    async def listen_and_transcribe(
        self,
        duration: float = 5.0,
        on_audio_level: Optional[callable] = None
    ) -> str:
        """
        Record and transcribe in one call.
        
        Args:
            duration: Max recording duration
            on_audio_level: Callback for visualization
            
        Returns:
            Transcribed text
        """
        audio = await self.record_audio(
            duration=duration,
            on_audio_level=on_audio_level
        )
        
        return await self.transcribe(audio)


# Global instance
stt_engine = SpeechToText(model_size="base")
