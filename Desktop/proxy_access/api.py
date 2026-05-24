from __future__ import annotations

import base64
import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def parse_error_message(data: object, fallback: str = "Ошибка запроса") -> str:
    if isinstance(data, dict):
        detail = data.get("detail", fallback)
        if isinstance(detail, str) and detail.strip():
            return detail
        if isinstance(detail, list):
            messages = []
            for item in detail:
                if isinstance(item, dict) and "msg" in item:
                    messages.append(str(item["msg"]))
            if messages:
                return "; ".join(messages)
        if detail:
            return str(detail)

    if isinstance(data, str) and data.strip():
        return data

    return fallback


def _decode_token_expiry(token: str) -> int | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)

    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        data = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    expires_at = data.get("exp")
    if isinstance(expires_at, int):
        return expires_at

    return None


def _token_expires_soon(token: str, threshold_seconds: int = 60) -> bool:
    expires_at = _decode_token_expiry(token)
    if expires_at is None:
        return False
    return expires_at - int(time.time()) <= threshold_seconds


def _parse_json_response(response: httpx.Response, url: str) -> dict[str, Any] | list[Any]:
    body = response.text.strip()
    if not body:
        if response.status_code >= 400:
            raise ApiError(
                f"Сервер вернул пустой ответ (HTTP {response.status_code}). "
                f"Проверьте backend и адрес API: {url}",
                response.status_code,
            )
        return {}

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower() and body.startswith(("<!DOCTYPE", "<html", "<!doctype")):
        raise ApiError(
            "Сервер вернул HTML вместо JSON. "
            "Проверьте PROXY_ACCESS_API_URL: он должен указывать на backend, а не на frontend.",
            response.status_code,
        )

    try:
        data = response.json()
    except ValueError as exc:
        snippet = body[:160].replace("\n", " ")
        raise ApiError(
            f"Некорректный ответ сервера (HTTP {response.status_code}): {snippet}",
            response.status_code,
        ) from exc

    if response.status_code >= 400:
        raise ApiError(parse_error_message(data), response.status_code)

    return data


class ApiClient:
    def __init__(
        self,
        api_url: str,
        *,
        access_token: str = "",
        refresh_token: str = "",
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = refresh_token

    def configure(
        self,
        api_url: str,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        if access_token is not None:
            self.access_token = access_token
        if refresh_token is not None:
            self.refresh_token = refresh_token

    def export_tokens(self) -> tuple[str, str]:
        return self.access_token, self.refresh_token

    def check_health(self) -> None:
        data = self._request_json("GET", "/")
        if not isinstance(data, dict) or data.get("status") != "ok":
            raise ApiError(
                "Сервер ответил, но это не backend Proxy Access. "
                "Проверьте PROXY_ACCESS_API_URL в Desktop/.env"
            )

    def activate_key(self, activation_key: str) -> dict[str, Any]:
        data = self._request_json(
            "POST",
            "/api/activate-key",
            json={"activation_key": activation_key.strip()},
        )
        if not isinstance(data, dict):
            raise ApiError("Некорректный ответ сервера")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not isinstance(access_token, str) or not isinstance(refresh_token, str):
            raise ApiError("Сервер не вернул токены для продолжения сессии")

        self.access_token = access_token
        self.refresh_token = refresh_token
        return data

    def refresh_access_token(self) -> str:
        if not self.refresh_token:
            raise ApiError("Сессия истекла. Активируйте ключ снова.", 401)

        data = self._request_json(
            "POST",
            "/auth/refresh",
            json={"refresh_token": self.refresh_token},
            allow_refresh=False,
        )
        if not isinstance(data, dict):
            raise ApiError("Некорректный ответ сервера")

        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ApiError("Сервер не вернул новый access token")

        self.access_token = access_token
        return access_token

    def ensure_fresh_access_token(self) -> str:
        if not self.access_token:
            if self.refresh_token:
                return self.refresh_access_token()
            raise ApiError("Сессия неактивна. Активируйте ключ снова.", 401)

        if _token_expires_soon(self.access_token):
            return self.refresh_access_token()

        return self.access_token

    def list_virtual_machines(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "/api/virtual-machines", auth=True)
        if not isinstance(data, list):
            raise ApiError("Некорректный ответ сервера")
        return data

    def connect_to_vm(self) -> dict[str, Any]:
        data = self._request_json("POST", "/api/connect", auth=True)
        if not isinstance(data, dict):
            raise ApiError("Некорректный ответ сервера")
        return data

    def disconnect_from_vm(self) -> dict[str, Any]:
        data = self._request_json("POST", "/api/disconnect", auth=True)
        if not isinstance(data, dict):
            raise ApiError("Некорректный ответ сервера")
        return data

    def status_websocket_url(self) -> str:
        token = self.ensure_fresh_access_token()
        base = self.api_url
        if base.startswith("https://"):
            ws_base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            ws_base = "ws://" + base[len("http://") :]
        else:
            ws_base = f"ws://{base}"

        query = urlencode({"token": token})
        return f"{ws_base}/ws/connection-status?{query}"

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        auth: bool = False,
        allow_refresh: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        headers = dict(kwargs.pop("headers", {}))
        url = f"{self.api_url}{path}"

        if auth:
            token = self.ensure_fresh_access_token() if allow_refresh else self.access_token
            if not token:
                raise ApiError("Сессия истекла. Активируйте ключ снова.", 401)
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = httpx.request(method, url, timeout=15.0, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiError(f"Не удалось связаться с сервером: {url}") from exc

        try:
            return _parse_json_response(response, url)
        except ApiError as exc:
            if exc.status_code == 401 and auth and allow_refresh and self.refresh_token:
                self.refresh_access_token()
                return self._request_json(
                    method,
                    path,
                    auth=True,
                    allow_refresh=False,
                    headers=headers,
                    **kwargs,
                )
            raise
