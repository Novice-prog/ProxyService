from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token
from app.db.deps import get_db
from app.db.models import User, VirtualMachine
from app.schemas.activation import ActivationKeyRequest, ActivationKeyResponse
from app.schemas.vm import ProxyConnectionResponse

router = APIRouter(prefix="/api", tags=["Activation"])


@router.post("/activate-key", response_model=ActivationKeyResponse)
def activate_key(
    data: ActivationKeyRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.activation_key == data.activation_key))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation key",
        )

    if user.activation_key_expires is not None:
        expires_at = user.activation_key_expires
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation key expired",
            )

    # Consume the one-time key before any other writes
    user.activation_key = None
    user.activation_key_expires = None

    # Reuse existing VM if user already has one; otherwise claim a free one.
    # Both operations happen inside a single transaction with the key clear above.
    vm = db.scalar(
        select(VirtualMachine).where(VirtualMachine.current_user_id == user.id)
    )
    if vm is None:
        vm = db.scalar(
            select(VirtualMachine)
            .where(
                VirtualMachine.is_active.is_(True),
                VirtualMachine.current_user_id.is_(None),
            )
            .order_by(VirtualMachine.id)
            .with_for_update(skip_locked=True)
        )
        if vm is not None:
            vm.current_user_id = user.id
            vm.last_used_at = datetime.now(UTC)

    # Single commit — key consumption + VM assignment are atomic
    db.commit()

    proxy = None
    vm_id = None
    if vm is not None:
        db.refresh(vm)
        vm_id = vm.id
        proxy = ProxyConnectionResponse(
            host=vm.host,
            port=vm.port,
            protocol=vm.protocol,
        )

    return ActivationKeyResponse(
        status="activated",
        user_id=user.id,
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        vm_id=vm_id,
        proxy=proxy,
    )
