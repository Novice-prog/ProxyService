from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.db.deps import get_db
from app.db.models import User, VirtualMachine
from app.schemas.vm import ProxyConnectionResponse, VirtualMachinePublicResponse

router = APIRouter(prefix="/api", tags=["User Virtual Machines"])


@router.get(
    "/virtual-machines",
    response_model=list[VirtualMachinePublicResponse],
    dependencies=[Depends(get_current_active_user)],
)
def list_virtual_machines(db: Session = Depends(get_db)):
    return db.scalars(
        select(VirtualMachine)
        .where(VirtualMachine.is_active.is_(True))
        .order_by(VirtualMachine.id)
    ).all()


@router.post("/connect")
def connect_user_to_vm(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    existing = db.scalar(
        select(VirtualMachine).where(VirtualMachine.current_user_id == current_user.id)
    )
    if existing is not None:
        return _connection_payload(existing)

    vm = db.scalar(
        select(VirtualMachine)
        .where(
            VirtualMachine.is_active.is_(True),
            VirtualMachine.current_user_id.is_(None),
        )
        .order_by(VirtualMachine.id)
        .with_for_update(skip_locked=True)
    )
    if vm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="All proxies are busy",
        )

    vm.current_user_id = current_user.id
    vm.last_used_at = datetime.now(UTC)
    db.commit()
    db.refresh(vm)
    return _connection_payload(vm)


@router.post("/disconnect")
def disconnect_user_from_vm(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    vm = db.scalar(
        select(VirtualMachine).where(VirtualMachine.current_user_id == current_user.id)
    )
    if vm is None:
        return {"status": "disconnected", "vm_id": None, "proxy": None}

    vm.current_user_id = None
    db.commit()
    return {"status": "disconnected", "vm_id": None, "proxy": None}


def _connection_payload(vm: VirtualMachine) -> dict:
    return {
        "status": "connected",
        "vm_id": vm.id,
        "proxy": ProxyConnectionResponse(
            host=vm.host,
            port=vm.port,
            protocol=vm.protocol,
        ).model_dump(),
    }
