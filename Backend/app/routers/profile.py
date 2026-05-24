from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password
from app.db.deps import get_db
from app.db.models import User, VirtualMachine
from app.schemas.user import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    RefreshKeyResponse,
    UserResponse,
)
from app.services.vm_pool import ensure_free_vm_or_503
from app.tasks.activation_keys import issue_activation_key
from app.tasks.email import send_activation_key

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/refresh-key", response_model=RefreshKeyResponse)
@limiter.limit("5/minute")
def refresh_activation_key(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):

    assigned_vm = db.scalar(
        select(VirtualMachine).where(VirtualMachine.current_user_id == current_user.id)
    )
    if assigned_vm is None:
        ensure_free_vm_or_503(db)

    activation_key = issue_activation_key(db=db, user=current_user)

    db.commit()
    db.refresh(current_user)

    send_activation_key.delay(
        email=current_user.email,
        activation_key=activation_key,
    )

    return {
        "activation_key": None,
        "activation_key_expires": current_user.activation_key_expires,
        "message": "Activation key refreshed successfully",
    }


@router.post("/change-password", response_model=ChangePasswordResponse)
@limiter.limit("10/minute")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if data.new_password != data.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match",
        )

    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}
