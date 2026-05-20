from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


TokenType = Literal["access", "refresh", "admin_access", "admin_refresh"]

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_token(*, subject: str | int, token_type: TokenType, expires_delta: timedelta) -> str:
    expires_at = datetime.now(UTC) + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

def create_access_token(subject: str | int) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

def create_refresh_token(subject: str | int) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days)
    )

def create_admin_access_token(subject: str | int) -> str:
    return create_token(
        subject=subject,
        token_type="admin_access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

def create_admin_refresh_token(subject: str | int) -> str:
    return create_token(
        subject=subject,
        token_type="admin_refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )

def decode_token(token: str) -> dict[str, Any] | None:
    try: 
        return jwt.decode(
            token, 
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError: 
        return None
    
def get_token_subject(token: str, expected_type: TokenType = "access") -> str | None:
    payload = decode_token(token)

    if payload is None:
        return None

    if payload.get("type") != expected_type:
        return None

    subject = payload.get("sub")

    if subject is None:
        return None

    return str(subject)

def generate_activation_key()-> str:
    return token_urlsafe(settings.activation_key_bytes)
