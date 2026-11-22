from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
from app.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Tracks WebSocket clients subscribed to each job."""

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(job_id, set()).add(websocket)
        logger.info("ws_connected", job_id=job_id, total=len(self.connections[job_id]))

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.connections:
            self.connections[job_id].discard(websocket)
            if not self.connections[job_id]:
                del self.connections[job_id]

    async def broadcast(self, job_id: str, event: dict):
        """Send an event to all clients watching this job."""
        if job_id not in self.connections:
            return

        dead = set()
        for ws in self.connections[job_id]:
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            self.connections[job_id].discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def job_events(websocket: WebSocket, job_id: str):
    """Frontend connects here to receive live agent events for a specific job."""
    await manager.connect(job_id, websocket)
    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)