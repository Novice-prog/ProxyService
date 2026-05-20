from datetime import UTC, datetime, timedelta

from app.core.security import hash_password
from app.db.models import ProxyProtocol, User, VirtualMachine


def test_activate_key_success(client, db_session):
    user = User(
        email="activate@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
        activation_key="test-activation-key-12345",
        activation_key_expires=datetime.now(UTC) + timedelta(days=1),
    )
    vm = VirtualMachine(
        name="Test VM",
        host="10.0.0.1",
        port=1080,
        protocol=ProxyProtocol.HTTP,
        is_active=True,
    )
    db_session.add(user)
    db_session.add(vm)
    db_session.commit()

    response = client.post(
        "/api/activate-key",
        json={"activation_key": "test-activation-key-12345"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "activated"
    assert data["user_id"] == user.id
    assert "access_token" in data
    assert "refresh_token" in data


def test_activate_key_invalid(client):
    response = client.post(
        "/api/activate-key",
        json={"activation_key": "wrong-activation-key"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid activation key"
