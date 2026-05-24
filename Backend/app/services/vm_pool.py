from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import VirtualMachine


def has_free_vm(db: Session) -> bool:
    free_id = db.scalar(
        select(VirtualMachine.id)
        .where(
            VirtualMachine.is_active.is_(True),
            VirtualMachine.current_user_id.is_(None),
        )
        .limit(1)
    )
    return free_id is not None


def ensure_free_vm_or_503(db: Session) -> None:
    if not has_free_vm(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="All proxies are busy. Try again later.",
        )
