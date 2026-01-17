"""
Neon Pi - Wake Word Detection
Uses OpenWakeWord for always-on "Hey Neon" detection.
"""
import asyncio
import numpy as np
import threading
from typing import Callable, Optional
import queue


class WakeWordDetector:
    """
    Wake word detector using OpenWakeWord.
    Uses pre-trained 'hey_jarvis' model temporarily until custom 'hey_neon' is trained.
    """
    
    def __init__(
        self,
        wake_word: str = "hey_jarvis",  # Temporary until we train "hey_neon"
        sensitivity: float = 0.5,
        on_wake: Optional[Callable] = None
    ):
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.on_wake = on_wake
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._audio_queue = queue.Queue()
        self._model = None
        self._stream = None
    
    def _load_model(self):
        """Load the OpenWakeWord model."""
        try:
            from openwakeword.model import Model
            
            # Load pre-trained model
            self._model = Model(
                wakeword_models=[self.wake_word],
                inference_framework="onnx"
            )
            print(f"[WakeWord] Loaded model: {self.wake_word}")
            return True
        except ImportError:
            print("[WakeWord] OpenWakeWord not installed. Install with: pip install openwakeword")
            return False
        except Exception as e:
            print(f"[WakeWord] Error loading model: {e}")
            return False
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream - adds audio to queue."""
        if status:
            print(f"[Audio] Status: {status}")
        self._audio_queue.put(indata.copy())
    
    def _detection_loop(self):
        """Main detection loop running in thread."""
        try:
            import sounddevice as sd
            
            # Audio parameters
            sample_rate = 16000
            chunk_size = 1280  # ~80ms at 16kHz
            
            print("[WakeWord] Starting microphone stream...")
            
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=chunk_size,
                callback=self._audio_callback
            ):
                print(f"[WakeWord] Listening for '{self.wake_word}'...")
                
                while self._running:
                    try:
                        # Get audio chunk from queue
                        audio_chunk = self._audio_queue.get(timeout=0.5)
                        
                        # Process with wake word model
                        prediction = self._model.predict(audio_chunk.flatten())
                        
                        # Check for wake word activation
                        for model_name, score in prediction.items():
                            if score > self.sensitivity:
                                print(f"[WakeWord] Detected '{model_name}' with score {score:.2f}")
                                
                                if self.on_wake:
                                    # Call the async callback
                                    asyncio.run(self.on_wake())
                                
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"[WakeWord] Processing error: {e}")
                        
        except Exception as e:
            print(f"[WakeWord] Stream error: {e}")
        finally:
            print("[WakeWord] Detection stopped")
    
    def start(self):
        """Start wake word detection in background thread."""
        if self._running:
            print("[WakeWord] Already running")
            return
        
        if not self._load_model():
            print("[WakeWord] Failed to load model, not starting")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Started background detection")
    
    def stop(self):
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("[WakeWord] Stopped")
    
    def is_running(self) -> bool:
        """Check if detection is active."""
        return self._running


# Pre-configured detector instance
wake_detector = WakeWordDetector()
