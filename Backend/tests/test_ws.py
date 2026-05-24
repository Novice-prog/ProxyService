from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.core.security import create_access_token, hash_password
from app.db.models import ProxyProtocol, User, VirtualMachine
from tests.conftest import TestSessionLocal


@pytest.fixture(autouse=True)
def patch_ws_session():
    """ws.py uses SessionLocal directly (not DI), so patch it to the test in-memory DB."""
    with patch("app.routers.ws.SessionLocal", TestSessionLocal):
        yield


def _make_user(db, email="ws@test.com"):
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_ws_connected_status(client, db_session):
    user = _make_user(db_session)
    vm = VirtualMachine(
        name="vm-connected",
        host="10.0.0.1",
        port=1080,
        protocol=ProxyProtocol.SOCKS,
        is_active=True,
        current_user_id=user.id,
        last_used_at=datetime.now(UTC),
    )
    db_session.add(vm)
    db_session.commit()

    token = create_access_token(user.id)
    with client.websocket_connect(f"/ws/connection-status?token={token}") as ws:
        payload = ws.receive_json()

    assert payload["status"] == "connected"
    assert payload["proxy"]["host"] == "10.0.0.1"
    assert payload["proxy"]["port"] == 1080


def test_ws_disconnected_when_free_vm_exists(client, db_session):
    user = _make_user(db_session, email="dis@test.com")
    db_session.add(
        VirtualMachine(
            name="vm-free",
            host="10.0.0.2",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=True,
            current_user_id=None,
        )
    )
    db_session.commit()

    token = create_access_token(user.id)
    with client.websocket_connect(f"/ws/connection-status?token={token}") as ws:
        payload = ws.receive_json()

    assert payload["status"] == "disconnected"


def test_ws_no_free_vms_status(client, db_session):
    user = _make_user(db_session, email="nofree@test.com")

    other = User(
        email="busy@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    db_session.add(
        VirtualMachine(
            name="vm-busy",
            host="10.0.0.3",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=True,
            current_user_id=other.id,
            last_used_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    token = create_access_token(user.id)
    with client.websocket_connect(f"/ws/connection-status?token={token}") as ws:
        payload = ws.receive_json()

    assert payload["status"] == "no_free_vms"
    assert payload["message"] == "All proxies are busy"


def test_ws_error_status_on_db_failure(client, db_session):
    user = _make_user(db_session, email="err@test.com")
    token = create_access_token(user.id)

    def boom(*args, **kwargs):
        raise RuntimeError("DB is down")

    with patch("app.routers.ws._fetch_vm_status", side_effect=boom):
        with client.websocket_connect(f"/ws/connection-status?token={token}") as ws:
            payload = ws.receive_json()

    assert payload["status"] == "error"
    assert "DB is down" in payload["detail"]


def test_ws_rejects_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/connection-status?token=invalid-token") as ws:
            ws.receive_json()


def test_ws_expired_activation_key_user_sees_no_free_vms(client, db_session):
    """User with valid token but no VM and no free VMs in pool → no_free_vms."""
    user = User(
        email="expkey@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
        activation_key="some-key",
        activation_key_expires=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id)
    with client.websocket_connect(f"/ws/connection-status?token={token}") as ws:
        payload = ws.receive_json()

    assert payload["status"] == "no_free_vms"
