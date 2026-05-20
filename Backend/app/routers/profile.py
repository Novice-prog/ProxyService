from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.tasks.activation_keys import issue_activation_key
from app.tasks.email import send_activation_key
from app.core.security import hash_password, verify_password
from app.schemas.user import ChangePasswordRequest, ChangePasswordResponse, RefreshKeyResponse, UserResponse
from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.deps import get_db

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/refresh-key", response_model=RefreshKeyResponse)
def refresh_activation_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
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
def change_password(
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
