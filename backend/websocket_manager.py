"""
Neon Pi - WebSocket Manager
Handles real-time communication with the frontend.
"""
from fastapi import WebSocket
from typing import Dict, Set, Any
import json
import asyncio


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        print(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket] Error sending to client: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = set()
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"[WebSocket] Broadcast error: {e}")
                    disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_state_update(self, state: str, data: Dict[str, Any] = None):
        """Send a state update to all clients."""
        message = {
            "type": "state_update",
            "state": state,
            "data": data or {}
        }
        await self.broadcast(message)
    
    async def send_transcript(self, text: str, is_final: bool = False):
        """Send transcription update."""
        await self.broadcast({
            "type": "transcript",
            "text": text,
            "is_final": is_final
        })
    
    async def send_response(self, text: str):
        """Send AI response text."""
        await self.broadcast({
            "type": "response",
            "text": text
        })
    
    async def send_spotify_update(self, data: Dict[str, Any]):
        """Send Spotify now playing update."""
        await self.broadcast({
            "type": "spotify",
            "data": data
        })
    
    async def send_error(self, error: str):
        """Send error message."""
        await self.broadcast({
            "type": "error",
            "message": error
        })


# Global instance
manager = ConnectionManager()
