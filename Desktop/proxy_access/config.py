from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

DESKTOP_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(DESKTOP_ROOT / ".env")

DEFAULT_API_URL = "http://127.0.0.1:8000"
SESSION_FILE = Path(os.environ.get("APPDATA", str(Path.home()))) / "ProxyAccess" / "session.json"


@dataclass
class ProxyInfo:
    host: str
    port: int
    protocol: str

    @property
    def connection_line(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


@dataclass
class Session:
    api_url: str
    user_id: int
    access_token: str = ""
    refresh_token: str = ""
    proxy: ProxyInfo | None = None
    vm_id: int | None = None
    activated_proxy: ProxyInfo | None = None
    activated_vm_id: int | None = None

    @property
    def is_connected(self) -> bool:
        return self.proxy is not None

    @property
    def has_tokens(self) -> bool:
        return bool(self.access_token and self.refresh_token)

    @property
    def proxy_label(self) -> str:
        if not self.proxy:
            return "Не подключено"
        return self.proxy.connection_line

    def remember_activated_vm(self, proxy: ProxyInfo | None, vm_id: int | None) -> None:
        if proxy is not None and vm_id is not None:
            self.activated_proxy = proxy
            self.activated_vm_id = vm_id

    def to_dict(self) -> dict:
        return {
            "api_url": self.api_url,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "proxy": asdict(self.proxy) if self.proxy else None,
            "vm_id": self.vm_id,
            "activated_proxy": asdict(self.activated_proxy) if self.activated_proxy else None,
            "activated_vm_id": self.activated_vm_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        proxy_raw = data.get("proxy")
        proxy = ProxyInfo(**proxy_raw) if proxy_raw else None

        activated_raw = (
            data.get("activated_proxy")
            or data.get("last_proxy")
            or proxy_raw
        )
        activated_proxy = ProxyInfo(**activated_raw) if activated_raw else None
        activated_vm_id = (
            data.get("activated_vm_id")
            or data.get("last_vm_id")
            or data.get("vm_id")
        )

        return cls(
            api_url=str(data["api_url"]),
            user_id=int(data["user_id"]),
            access_token=str(data.get("access_token", "")),
            refresh_token=str(data.get("refresh_token", "")),
            proxy=proxy,
            vm_id=data.get("vm_id"),
            activated_proxy=activated_proxy,
            activated_vm_id=activated_vm_id,
        )


def load_session() -> Session | None:
    if not SESSION_FILE.exists():
        return None

    try:
        session = Session.from_dict(json.loads(SESSION_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

    session.api_url = api_url_from_env()
    return session


def save_session(session: Session | None) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    if session is None:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        return

    SESSION_FILE.write_text(
        json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def api_url_from_env() -> str:
    return os.environ.get("PROXY_ACCESS_API_URL", DEFAULT_API_URL).strip() or DEFAULT_API_URL
