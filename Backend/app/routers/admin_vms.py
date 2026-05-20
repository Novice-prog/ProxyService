from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import ProxyProtocol, VirtualMachine
from app.db.deps import get_db
from app.schemas.vm import VirtualMachineCreate, VirtualMachineResponse, VirtualMachineUpdate
from app.core.dependencies import get_current_admin

router = APIRouter(
    prefix="/admin/virtual-machines",
    tags=["Admin Virtual Machines"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=list[VirtualMachineResponse])
def list_virtual_machines(db: Session = Depends(get_db)):
    return db.scalars(select(VirtualMachine).order_by(VirtualMachine.id)).all()


@router.post(
    "",
    response_model=VirtualMachineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_virtual_machine(
    data: VirtualMachineCreate,
    db: Session = Depends(get_db),
):
    vm = VirtualMachine(
        name=data.name,
        host=data.host,
        port=data.port,
        protocol=ProxyProtocol(data.protocol.value),
        is_active=data.is_active,
    )

    db.add(vm)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Virtual machine with this host and port already exists",
        )

    db.refresh(vm)
    return vm


@router.patch(
    "/{vm_id}",
    response_model=VirtualMachineResponse,
)
def update_virtual_machine(
    vm_id: int,
    data: VirtualMachineUpdate,
    db: Session = Depends(get_db),
):
    vm = db.get(VirtualMachine, vm_id)

    if vm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Virtual machine not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "protocol" and value is not None:
            value = ProxyProtocol(value.value)
        setattr(vm, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Virtual machine with this host and port already exists",
        )

    db.refresh(vm)
    return vm


@router.post(
    "/{vm_id}/release",
    response_model=VirtualMachineResponse,
)
def release_virtual_machine(
    vm_id: int,
    db: Session = Depends(get_db),
):
    vm = db.get(VirtualMachine, vm_id)

    if vm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Virtual machine not found",
        )

    vm.current_user_id = None

    db.commit()
    db.refresh(vm)

    return vm


@router.delete(
    "/{vm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_virtual_machine(
    vm_id: int,
    db: Session = Depends(get_db),
):
    vm = db.get(VirtualMachine, vm_id)

    if vm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Virtual machine not found",
        )

    db.delete(vm)
    db.commit()
