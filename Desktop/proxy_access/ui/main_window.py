from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from proxy_access.api import ApiClient, ApiError
from proxy_access.config import (
    ProxyInfo,
    Session,
    api_url_from_env,
    load_session,
    save_session,
)
from proxy_access.ui.activate_dialog import ActivateKeyDialog
from proxy_access.ui.connection_panel import ConnectionPanel
from proxy_access.ui.sidebar import Sidebar
from proxy_access.ui.vm_card import VmCard
from proxy_access.workers import ApiWorker, StatusWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Proxy Access")
        self.setMinimumSize(960, 600)
        self.resize(1100, 680)

        self.session: Session | None = load_session()
        self.client = ApiClient(
            api_url_from_env(),
            access_token=self.session.access_token if self.session else "",
            refresh_token=self.session.refresh_token if self.session else "",
        )

        self.activation_worker: ApiWorker | None = None
        self.toggle_worker: ApiWorker | None = None
        self.status_worker: StatusWorker | None = None
        self._activation_dialog: ActivateKeyDialog | None = None

        self._build_ui()
        self._wire_signals()

        if self.session and self.session.has_tokens:
            self._render_session()
            self._start_status_worker()
        else:
            self._render_session()
            self._open_activation_dialog()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        center = QFrame()
        center.setObjectName("CenterPanel")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(28, 24, 24, 24)
        center_layout.setSpacing(18)

        header = QLabel("Серверы")
        header.setObjectName("CenterTitle")
        center_layout.addWidget(header)

        self.vm_card = VmCard()
        center_layout.addWidget(self.vm_card)

        self.center_hint = QLabel("")
        self.center_hint.setObjectName("CenterHint")
        self.center_hint.setWordWrap(True)
        self.center_hint.hide()
        center_layout.addWidget(self.center_hint)

        center_layout.addStretch()
        root_layout.addWidget(center, stretch=2)

        self.connection_panel = ConnectionPanel()
        root_layout.addWidget(self.connection_panel, stretch=1)

        self.setCentralWidget(root)
        self.statusBar().showMessage(f"Backend: {api_url_from_env()}")

    def _wire_signals(self) -> None:
        self.sidebar.add_clicked.connect(self._open_activation_dialog)
        self.sidebar.reset_clicked.connect(self._on_reset)
        self.connection_panel.toggle_requested.connect(self._on_toggle_requested)

    def _render_session(self) -> None:
        has_session = bool(self.session and self.session.has_tokens)
        self.connection_panel.set_session_available(has_session)

        if not self.session:
            self.vm_card.set_vm(vm_id=None, proxy=None)
            self.connection_panel.set_status(status="disconnected")
            self.center_hint.setText(
                "Нет активной сессии. Нажмите «+» в сайдбаре, чтобы активировать ключ."
            )
            self.center_hint.show()
            return

        is_connected = self.session.is_connected
        self.vm_card.set_vm(
            vm_id=self.session.activated_vm_id,
            proxy=self.session.activated_proxy,
            is_connected=is_connected,
        )

        if is_connected:
            self.connection_panel.set_status(
                status="connected",
                vm_id=self.session.vm_id,
                proxy=self.session.proxy,
            )
            self.center_hint.hide()
        else:
            self.connection_panel.set_status(status="disconnected")
            if self.session.activated_proxy is not None:
                self.center_hint.setText(
                    "Прокси отключён. Нажмите большой круг справа, чтобы подключиться."
                )
            else:
                self.center_hint.setText(
                    "Сессия активна, но сервер не активирован. "
                    "Используйте «+» в сайдбаре, чтобы активировать ключ."
                )
            self.center_hint.show()

    def _open_activation_dialog(self) -> None:
        if self._activation_dialog is not None:
            self._activation_dialog.raise_()
            self._activation_dialog.activateWindow()
            return

        dialog = ActivateKeyDialog(self)
        self._activation_dialog = dialog
        dialog.submitted.connect(lambda key: self._submit_activation(dialog, key))
        dialog.finished.connect(lambda _result: self._on_activation_dialog_closed())
        dialog.show()

    def _submit_activation(self, dialog: ActivateKeyDialog, key: str) -> None:
        dialog.set_busy(True)
        self.client.configure(api_url_from_env(), access_token="", refresh_token="")

        def task() -> dict:
            self.client.check_health()
            return self.client.activate_key(key)

        self.activation_worker = ApiWorker(task)
        self.activation_worker.succeeded.connect(
            lambda payload: self._on_activation_success(dialog, payload)
        )
        self.activation_worker.failed.connect(
            lambda error: self._on_activation_failed(dialog, error)
        )
        self.activation_worker.finished.connect(self._on_activation_finished)
        self.activation_worker.start()

    def _on_activation_success(self, dialog: ActivateKeyDialog, payload: object) -> None:
        if not isinstance(payload, dict):
            dialog.set_busy(False)
            dialog.show_error("Сервер вернул неожиданный ответ.")
            return

        self.session = self._session_from_activation(payload)
        save_session(self.session)
        self._sync_client_from_session()
        self._render_session()
        self._start_status_worker()

        self.statusBar().showMessage("Сессия активирована", 5000)
        dialog.accept()

    def _on_activation_failed(self, dialog: ActivateKeyDialog, error: object) -> None:
        dialog.set_busy(False)
        dialog.show_error(str(error))
        self.statusBar().showMessage("Активация не удалась", 5000)

    def _on_activation_finished(self) -> None:
        self.activation_worker = None

    def _on_activation_dialog_closed(self) -> None:
        self._activation_dialog = None

    def _on_toggle_requested(self, wants_connect: bool) -> None:
        if not self.session or not self.session.has_tokens:
            return
        if self.toggle_worker is not None and self.toggle_worker.isRunning():
            return

        self._sync_client_from_session()

        if wants_connect:
            task = self.client.connect_to_vm
            loading_msg = "Ищем свободный прокси…"
        else:
            task = self.client.disconnect_from_vm
            loading_msg = "Освобождаем прокси…"

        self.connection_panel.show_loading(loading_msg)

        self.toggle_worker = ApiWorker(task)
        self.toggle_worker.succeeded.connect(
            lambda payload: self._on_toggle_success(wants_connect, payload)
        )
        self.toggle_worker.failed.connect(
            lambda error: self._on_toggle_failed(wants_connect, error)
        )
        self.toggle_worker.finished.connect(self._on_toggle_finished)
        self.toggle_worker.start()

    def _on_toggle_success(self, wanted_connect: bool, payload: object) -> None:
        if not self.session:
            return

        self._sync_session_tokens()

        if not isinstance(payload, dict):
            self.connection_panel.set_status(
                status="error",
                custom_message="Сервер вернул неожиданный ответ",
                vm_id=self.session.vm_id,
                proxy=self.session.proxy,
            )
            return

        self.session.proxy = self._proxy_from_payload(payload.get("proxy"))
        self.session.vm_id = payload.get("vm_id")

        save_session(self.session)
        self._render_session()

        action = "подключение" if wanted_connect else "отключение"
        self.statusBar().showMessage(f"Успешное {action}", 3000)

    def _on_toggle_failed(self, wanted_connect: bool, error: object) -> None:
        if isinstance(error, ApiError) and error.status_code == 401:
            self._handle_session_expired(str(error))
            return

        if (
            wanted_connect
            and isinstance(error, ApiError)
            and error.status_code == 503
        ):
            self.connection_panel.set_status(
                status="no_free_vms",
                vm_id=self.session.vm_id if self.session else None,
                proxy=self.session.proxy if self.session else None,
                custom_message=str(error),
            )
            self.statusBar().showMessage("Свободных прокси нет", 4000)
            return

        self.connection_panel.set_status(
            status="error",
            vm_id=self.session.vm_id if self.session else None,
            proxy=self.session.proxy if self.session else None,
            custom_message=str(error),
        )
        self.statusBar().showMessage(f"Ошибка: {error}", 5000)

    def _on_toggle_finished(self) -> None:
        self.toggle_worker = None

    def _sync_session_tokens(self) -> None:
        if not self.session:
            return
        access, refresh = self.client.export_tokens()
        if (access, refresh) != (self.session.access_token, self.session.refresh_token):
            self.session.access_token = access
            self.session.refresh_token = refresh
            save_session(self.session)

    def _start_status_worker(self) -> None:
        if not self.session or not self.session.has_tokens:
            return

        self._stop_status_worker()
        self.status_worker = StatusWorker(self.client)
        self.status_worker.status_changed.connect(self._on_status)
        self.status_worker.connection_error.connect(self._on_status_error)
        self.status_worker.authentication_expired.connect(self._on_status_auth_expired)
        self.status_worker.tokens_updated.connect(self._on_status_tokens_updated)
        self.status_worker.start()

    def _stop_status_worker(self) -> None:
        if self.status_worker:
            self.status_worker.stop()
            self.status_worker.wait(2000)
            self.status_worker = None

    def _on_status(self, payload: dict) -> None:
        if not self.session:
            return

        status = str(payload.get("status", "disconnected"))
        proxy = self._proxy_from_payload(payload.get("proxy"))
        message = payload.get("message") or payload.get("detail")

        if status == "connected" and proxy:
            changed = (
                self.session.proxy is None
                or self.session.proxy.connection_line != proxy.connection_line
            )
            self.session.proxy = proxy
            if changed:
                save_session(self.session)

            self.connection_panel.set_status(
                status="connected",
                vm_id=self.session.vm_id,
                proxy=proxy,
            )
            self.vm_card.set_vm(
                vm_id=self.session.activated_vm_id,
                proxy=self.session.activated_proxy,
                is_connected=True,
            )
            self.center_hint.hide()
            self.statusBar().showMessage("Подключение активно", 3000)
            return

        if status in {"no_free_vms", "error"}:
            self.connection_panel.set_status(
                status=status,
                vm_id=self.session.vm_id,
                proxy=self.session.proxy,
                custom_message=str(message) if message else None,
            )
            return

        if self.session.is_connected:
            self.session.proxy = None
            self.session.vm_id = None
            save_session(self.session)
        self.connection_panel.set_status(status="disconnected")
        self.vm_card.set_vm(
            vm_id=self.session.activated_vm_id,
            proxy=self.session.activated_proxy,
            is_connected=False,
        )
        if self.session.activated_proxy is not None:
            self.center_hint.setText(
                "Прокси отключён. Нажмите большой круг, чтобы переподключиться."
            )
        else:
            self.center_hint.setText("Сервер сообщил, что подключение завершено.")
        self.center_hint.show()

    def _on_status_error(self, message: str) -> None:
        vm_id = self.session.vm_id if self.session else None
        proxy = self.session.proxy if self.session else None
        self.connection_panel.set_status(
            status="error",
            vm_id=vm_id,
            proxy=proxy,
            custom_message=f"Мониторинг переподключается… ({message})",
        )

    def _on_status_auth_expired(self, message: str) -> None:
        self._handle_session_expired(message)

    def _on_status_tokens_updated(self, access_token: str, refresh_token: str) -> None:
        if not self.session:
            return
        self.session.access_token = access_token
        self.session.refresh_token = refresh_token
        save_session(self.session)

    def _on_reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Сбросить сессию",
            "Удалить локальную сессию и вернуться к активации ключа?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._stop_status_worker()
        self.session = None
        self.client.configure(api_url_from_env(), access_token="", refresh_token="")
        save_session(None)
        self._render_session()
        self.statusBar().showMessage("Сессия сброшена", 5000)
        self._open_activation_dialog()

    def _handle_session_expired(self, message: str) -> None:
        self._stop_status_worker()
        self.session = None
        self.client.configure(api_url_from_env(), access_token="", refresh_token="")
        save_session(None)
        self._render_session()
        self.statusBar().showMessage(f"Сессия завершена: {message}", 6000)
        self._open_activation_dialog()

    def _sync_client_from_session(self) -> None:
        if not self.session:
            return
        self.client.configure(
            api_url_from_env(),
            access_token=self.session.access_token,
            refresh_token=self.session.refresh_token,
        )

    def _proxy_from_payload(self, payload: dict | None) -> ProxyInfo | None:
        if not payload:
            return None
        try:
            return ProxyInfo(
                host=str(payload["host"]),
                port=int(payload["port"]),
                protocol=str(payload["protocol"]),
            )
        except (KeyError, ValueError, TypeError):
            return None

    def _session_from_activation(self, payload: dict) -> Session:
        proxy = self._proxy_from_payload(payload.get("proxy"))
        vm_id = payload.get("vm_id")
        return Session(
            api_url=api_url_from_env(),
            user_id=int(payload["user_id"]),
            access_token=str(payload.get("access_token", "")),
            refresh_token=str(payload.get("refresh_token", "")),
            proxy=proxy,
            vm_id=vm_id,
            activated_proxy=proxy,
            activated_vm_id=vm_id,
        )

    def closeEvent(self, event) -> None:
        self._stop_status_worker()
        super().closeEvent(event)
