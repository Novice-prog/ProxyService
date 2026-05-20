from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.db.models import ProxyProtocol


class VirtualMachineResponse(BaseModel):
    """Full VM info — only for admin endpoints."""
    id: int
    name: str
    host: str
    port: int
    protocol: ProxyProtocol
    is_active: bool
    current_user_id: int | None
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class VirtualMachinePublicResponse(BaseModel):
    """Public VM info — hides current_user_id to prevent user enumeration."""
    id: int
    name: str
    host: str
    port: int
    protocol: ProxyProtocol
    is_active: bool
    is_occupied: bool
    last_used_at: datetime | None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def derive_is_occupied(cls, data: Any) -> Any:
        # When coming from an ORM object, compute is_occupied from current_user_id
        if not isinstance(data, dict):
            return {
                "id": data.id,
                "name": data.name,
                "host": data.host,
                "port": data.port,
                "protocol": data.protocol,
                "is_active": data.is_active,
                "is_occupied": data.current_user_id is not None,
                "last_used_at": data.last_used_at,
            }
        return data


class VirtualMachineCreate(BaseModel):
    name: str
    host: str
    port: int = Field(ge=1, le=65535)
    protocol: ProxyProtocol
    is_active: bool = True


class VirtualMachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    protocol: ProxyProtocol | None = None
    is_active: bool | None = None


class ProxyConnectionResponse(BaseModel):
    host: str
    port: int
    protocol: ProxyProtocol
