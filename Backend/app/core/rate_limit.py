from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def _create_limiter() -> Limiter:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return Limiter(key_func=get_client_ip, enabled=False)

    return Limiter(
        key_func=get_client_ip,
        default_limits=[f"{settings.rate_limit_global_per_minute}/minute"],
        storage_uri=settings.redis_url,
        enabled=True,
    )


limiter = _create_limiter()
