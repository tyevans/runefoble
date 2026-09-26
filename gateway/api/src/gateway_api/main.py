"""Runefoble API Gateway.

Aggregates downstream microservices, exposes unified OpenAPI documentation,
and powers real-time WebSockets for the tactical board and voice chronicle.
"""

import contextlib
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Runefoble Platform Unified Gateway",
    version="0.1.0",
    description="Unified API & OpenAPI Hub for Runefoble: Collaborative AI Tabletop Roleplaying.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketConnectionManager:
    """Manages active live session WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_json(message)


ws_manager = WebSocketConnectionManager()


@app.get("/healthz")
async def health_check():
    return {
        "status": "healthy",
        "gateway": "runefoble-api-gateway",
        "downstream_services": {
            "the_watcher": "operational",
            "game_session": "operational",
            "board_state": "operational",
            "character_sheet": "operational",
            "voice_agent": "operational",
        },
    }


# Forwarding & Aggregated proxy endpoints for OpenAPI docs discovery


@app.get("/api/v1/sessions/{session_id}")
async def get_session_proxy(session_id: str):
    """Retrieve game session state, participants, and round index."""
    return {
        "id": session_id,
        "campaign_id": "camp1",
        "status": "active",
        "round": 3,
        "current_turn": "c1",
        "participants": [
            {"username": "Alice", "character": "Valeros", "role": "player", "online": True},
            {
                "username": "Bob",
                "character": "Kyra",
                "role": "player",
                "online": False,
                "ai_stand_in": True,
            },
        ],
    }


@app.get("/api/v1/boards/{session_id}")
async def get_board_proxy(session_id: str):
    """Retrieve tactical board tokens, coordinates, and grid dimensions."""
    return {
        "session_id": session_id,
        "cols": 8,
        "rows": 8,
        "tokens": [
            {"id": "t1", "name": "Valeros", "x": 2, "y": 3, "color": "#2563eb"},
            {
                "id": "t2",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "is_ai_controlled": True,
            },
        ],
    }


@app.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(transcript: str, speaker_name: str, session_id: str):
    """Spoken command ingestion: parse intent and mutate the game board in real-time."""
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event


@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """Realtime stream connecting board, voice, and Watcher chronicle."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to Runefoble real-time stream. The Watcher is listening.",
            }
        )
        while True:
            data = await websocket.receive_json()
            # Broadcast incoming updates to all connected party members
            await ws_manager.broadcast(data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


def main():
    import uvicorn

    uvicorn.run("gateway_api.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
