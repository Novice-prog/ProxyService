import asyncio

import anyio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import get_token_subject
from app.db.database import SessionLocal
from app.db.models import VirtualMachine

router = APIRouter(tags=["WebSocket"])


def _fetch_vm_status(user_id: int) -> dict:
    """Synchronous DB query — called via anyio.to_thread to avoid blocking the event loop."""
    with SessionLocal() as db:
        vm = db.scalar(
            select(VirtualMachine).where(VirtualMachine.current_user_id == user_id)
        )
        if vm is None:
            return {
                "status": "disconnected",
                "message": "User has no active proxy connection",
            }
        return {
            "status": "connected",
            "message": "User is connected to proxy",
            "proxy": {
                "host": vm.host,
                "port": vm.port,
                "protocol": vm.protocol,
            },
        }


@router.websocket("/ws/connection-status")
async def connection_status(
    websocket: WebSocket,
    token: str = Query(...),
):
    subject = get_token_subject(token, expected_type="access")
    if subject is None:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await websocket.accept()
    user_id = int(subject)

    try:
        while True:
            payload = await anyio.to_thread.run_sync(_fetch_vm_status, user_id)
            await websocket.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
