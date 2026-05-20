from pydantic import BaseModel, Field

from app.schemas.vm import ProxyConnectionResponse


class ActivationKeyRequest(BaseModel):
    activation_key: str = Field(min_length=16, max_length=128)


class ActivationKeyResponse(BaseModel):
    status: str
    user_id: int
    # Tokens issued on activation — desktop uses them for subsequent API calls
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    vm_id: int | None = None
    proxy: ProxyConnectionResponse | None = None


class ConnectionStatusResponse(BaseModel):
    status: str
    message: str | None = None
