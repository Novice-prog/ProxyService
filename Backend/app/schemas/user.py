from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime 

class UserResponse(BaseModel):
    id: int 
    email: EmailStr
    is_active: bool 
    has_pending_activation_key: bool
    activation_key_expires: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        'from_attributes': True
    }

    @model_validator(mode="before")
    @classmethod
    def derive_pending_key(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "email": data.email,
            "is_active": data.is_active,
            "has_pending_activation_key": data.activation_key is not None,
            "activation_key_expires": data.activation_key_expires,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)
    new_password_confirm: str = Field(min_length=8, max_length=72)

class ChangePasswordResponse(BaseModel):
    message: str

class RefreshKeyResponse(BaseModel):
    activation_key_expires: datetime | None
    message: str 

