from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from proxy_access.api import ApiClient, ApiError


class ApiWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(object)

    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self.task = task

    def run(self) -> None:
        try:
            payload = self.task()
            self.succeeded.emit(payload)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(exc)


class StatusWorker(QThread):
    status_changed = pyqtSignal(dict)
    connection_error = pyqtSignal(str)
    authentication_expired = pyqtSignal(str)
    tokens_updated = pyqtSignal(str, str)

    def __init__(self, client: ApiClient, reconnect_delay: float = 3.0) -> None:
        super().__init__()
        self.client = client
        self.reconnect_delay = reconnect_delay
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        # Импорт через `from` — если установлен не тот пакет `websocket`
        # (вместо `websocket-client`), здесь сразу будет ImportError с
        # понятным сообщением, а не AttributeError на каждой итерации.
        try:
            from websocket import create_connection, WebSocketTimeoutException
        except ImportError as exc:
            self.connection_error.emit(
                "Не найден пакет websocket-client. "
                "Запустите: pip install -r requirements.txt "
                f"(подробности: {exc})"
            )
            return

        while self._running:
            try:
                previous_access, previous_refresh = self.client.export_tokens()
                endpoint = self.client.status_websocket_url()
                current_access, current_refresh = self.client.export_tokens()
                if (
                    current_access != previous_access
                    or current_refresh != previous_refresh
                ):
                    self.tokens_updated.emit(current_access, current_refresh)

                connection = create_connection(endpoint, timeout=10)
                connection.settimeout(5)
                try:
                    while self._running:
                        try:
                            raw = connection.recv()
                        except WebSocketTimeoutException:
                            continue
                        if not raw:
                            continue

                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            self.connection_error.emit("Получен некорректный статус от сервера")
                            continue

                        if isinstance(payload, dict):
                            self.status_changed.emit(payload)
                finally:
                    connection.close()
            except ApiError as exc:
                if not self._running:
                    break
                if exc.status_code == 401:
                    self.authentication_expired.emit(str(exc))
                    break
                self.connection_error.emit(str(exc))
                time.sleep(self.reconnect_delay)
            except AttributeError as exc:
                # Конкретный случай: установлен заброшенный пакет `websocket`
                # вместо `websocket-client`. Без явного сообщения юзер не поймёт.
                self.connection_error.emit(
                    "Конфликт пакетов: похоже, установлен старый пакет 'websocket'. "
                    "Выполните: pip uninstall -y websocket && pip install websocket-client "
                    f"(детали: {exc})"
                )
                return
            except Exception as exc:  # noqa: BLE001
                if self._running:
                    self.connection_error.emit(str(exc))
                    time.sleep(self.reconnect_delay)
