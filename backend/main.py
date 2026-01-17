"""
Neon Pi - Main FastAPI Application
The main entry point for the Neon voice assistant.
"""
import asyncio
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn

from .config import settings
from .websocket_manager import manager
from .gemini_client import gemini_client
from .spotify_client import spotify_client
from .tts import tts_engine
from .speech_to_text import stt_engine
from .wake_word import WakeWordDetector
from .tools import tool_executor


# Application state
class AppState:
    """Global application state."""
    def __init__(self):
        self.is_listening = False
        self.is_processing = False
        self.is_speaking = False
        self.wake_detector: WakeWordDetector = None
        self.spotify_polling_task = None


state = AppState()


async def on_wake_word_detected():
    """Callback when wake word is detected."""
    if state.is_processing or state.is_speaking:
        return
    
    print("[Anton] Wake word detected!")
    state.is_listening = True
    
    # Notify UI
    await manager.send_state_update("listening")
    
    try:
        # Record and transcribe
        state.is_processing = True
        await manager.send_state_update("processing")
        
        # Listen for user speech
        transcript = await stt_engine.listen_and_transcribe(
            duration=10.0,
            on_audio_level=lambda level: manager.send_state_update(
                "listening", {"level": level}
            )
        )
        
        if not transcript:
            await manager.send_state_update("idle")
            state.is_processing = False
            return
        
        # Send transcript to UI
        await manager.send_transcript(transcript, is_final=True)
        
        # Process with Gemini
        await manager.send_state_update("thinking")
        response = await gemini_client.process_message(
            transcript,
            tool_executor=tool_executor.execute
        )
        
        # Send response to UI
        await manager.send_response(response)
        
        # Speak the response
        state.is_speaking = True
        await manager.send_state_update("speaking")
        
        audio = await tts_engine.speak(response)
        if audio:
            # Send audio to frontend for playback
            await manager.broadcast({
                "type": "audio",
                "data": audio.hex()  # Send as hex string
            })
        
    except Exception as e:
        print(f"[Anton] Error in wake word handler: {e}")
        await manager.send_error(str(e))
    finally:
        state.is_listening = False
        state.is_processing = False
        state.is_speaking = False
        await manager.send_state_update("idle")


async def spotify_polling_loop():
    """Poll Spotify for now playing updates."""
    while True:
        try:
            if spotify_client.is_authenticated():
                now_playing = await spotify_client.get_now_playing()
                if now_playing:
                    await manager.send_spotify_update(now_playing)
        except Exception as e:
            print(f"[Spotify] Polling error: {e}")
        
        await asyncio.sleep(2)  # Poll every 2 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("[Anton] Starting up...")
    
    # Try to load cached Spotify token
    spotify_client.load_cached_token()
    
    # Start Spotify polling
    state.spotify_polling_task = asyncio.create_task(spotify_polling_loop())
    
    # Initialize wake word detector
    state.wake_detector = WakeWordDetector(
        wake_word="hey_jarvis",  # Temporary until we train "hey_neon"
        sensitivity=0.5,
        on_wake=on_wake_word_detected
    )
    
    # Note: Wake word detection will be started by the client
    # after the user grants microphone permission
    
    print("[Anton] Ready! Say 'Hey Jarvis' to activate (Hey Neon coming soon)")
    
    yield
    
    # Shutdown
    print("[Anton] Shutting down...")
    
    if state.spotify_polling_task:
        state.spotify_polling_task.cancel()
    
    if state.wake_detector:
        state.wake_detector.stop()
    
    await tool_executor.close()


# Create FastAPI app
app = FastAPI(
    title="Neon Pi",
    description="AI Voice Assistant for Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan
)

# Determine frontend path
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"


# Mount static files
if FRONTEND_PATH.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")


# ==================== Routes ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    index_path = FRONTEND_PATH / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>Neon Pi</h1><p>Frontend not found</p>")


@app.get("/api/status")
async def get_status():
    """Get current system status."""
    return {
        "spotify_connected": spotify_client.is_authenticated(),
        "wake_word_active": state.wake_detector.is_running() if state.wake_detector else False,
        "is_listening": state.is_listening,
        "is_processing": state.is_processing,
        "is_speaking": state.is_speaking
    }


@app.get("/api/spotify/auth")
async def spotify_auth():
    """Start Spotify OAuth flow."""
    auth_url = spotify_client.get_auth_url()
    return {"auth_url": auth_url}


@app.get("/callback/spotify")
async def spotify_callback(code: str = None, error: str = None):
    """Spotify OAuth callback."""
    if error:
        return HTMLResponse(f"<h1>Error</h1><p>{error}</p>")
    
    if code:
        success = spotify_client.authenticate_with_code(code)
        if success:
            return HTMLResponse("""
                <h1>Spotify Connected!</h1>
                <p>You can close this tab and return to Neon.</p>
                <script>setTimeout(() => window.close(), 2000)</script>
            """)
    
    return HTMLResponse("<h1>Error</h1><p>Authentication failed</p>")


@app.post("/api/wake/start")
async def start_wake_detection():
    """Start wake word detection."""
    if state.wake_detector:
        state.wake_detector.start()
        return {"status": "started"}
    return {"status": "error", "message": "Wake detector not initialized"}


@app.post("/api/wake/stop")
async def stop_wake_detection():
    """Stop wake word detection."""
    if state.wake_detector:
        state.wake_detector.stop()
        return {"status": "stopped"}
    return {"status": "error"}


@app.post("/api/message")
async def send_message(request: Request):
    """Send a text message (for testing without voice)."""
    data = await request.json()
    message = data.get("message", "")
    
    if not message:
        return JSONResponse({"error": "No message provided"}, status_code=400)
    
    try:
        await manager.send_state_update("thinking")
        
        response = await gemini_client.process_message(
            message,
            tool_executor=tool_executor.execute
        )
        
        await manager.send_response(response)
        await manager.send_state_update("idle")
        
        return {"response": response}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket)
    
    try:
        # Send initial status
        await manager.send_personal(websocket, {
            "type": "connected",
            "spotify_authenticated": spotify_client.is_authenticated()
        })
        
        while True:
            data = await websocket.receive_json()
            
            # Handle client messages
            if data.get("type") == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
            
            elif data.get("type") == "start_listening":
                # Trigger manual listening (simulate wake word)
                await on_wake_word_detected()
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        await manager.disconnect(websocket)


# ==================== Main ====================

def main():
    """Run the Neon Pi server."""
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
