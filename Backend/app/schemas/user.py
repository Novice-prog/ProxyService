from pydantic import BaseModel, EmailStr, Field
from datetime import datetime 

class UserResponse(BaseModel):
    id: int 
    email: EmailStr
    is_active: bool 
    activation_key: str | None
    activation_key_expires: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        'from_attributes': True
    }

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)
    new_password_confirm: str = Field(min_length=8, max_length=72)

class ChangePasswordResponse(BaseModel):
    message: str

class RefreshKeyResponse(BaseModel):
    activation_key: str | None
    activation_key_expires: datetime | None
    message: str 

