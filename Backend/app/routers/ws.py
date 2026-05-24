import asyncio
import logging

import anyio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import get_token_subject
from app.db.database import SessionLocal
from app.db.models import VirtualMachine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


def _fetch_vm_status(user_id: int) -> dict:
    
    with SessionLocal() as db:
        vm = db.scalar(
            select(VirtualMachine).where(
                VirtualMachine.current_user_id == user_id,
                VirtualMachine.is_active.is_(True),
            )
        )
        if vm is not None:
            return {
                "status": "connected",
                "message": "User is connected to proxy",
                "proxy": {
                    "host": vm.host,
                    "port": vm.port,
                    "protocol": vm.protocol,
                },
            }

        free_vm_exists = db.scalar(
            select(VirtualMachine.id)
            .where(
                VirtualMachine.is_active.is_(True),
                VirtualMachine.current_user_id.is_(None),
            )
            .limit(1)
        )
        if free_vm_exists is None:
            return {
                "status": "no_free_vms",
                "message": "All proxies are busy",
            }

        return {
            "status": "disconnected",
            "message": "User has no active proxy connection",
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
            try:
                payload = await anyio.to_thread.run_sync(_fetch_vm_status, user_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to fetch VM status for user_id=%s", user_id)
                payload = {
                    "status": "error",
                    "message": "Failed to fetch connection status",
                    "detail": str(exc),
                }
            await websocket.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
