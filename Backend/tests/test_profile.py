from datetime import UTC, datetime, timedelta

from app.core.security import create_access_token, hash_password
from app.db.models import ProxyProtocol, User, VirtualMachine


def test_get_profile(client, db_session):
    user = User(
        email="profile@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id)

    response = client.get(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "profile@test.com"


def test_get_profile_without_token(client):
    response = client.get("/profile")

    assert response.status_code == 401


def _make_user(db_session, *, email: str = "refresh@test.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_refresh_key_success_when_free_vm_exists(client, db_session):
    user = _make_user(db_session)
    db_session.add(
        VirtualMachine(
            name="vm-free",
            host="10.0.0.1",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=True,
            current_user_id=None,
        )
    )
    db_session.commit()

    token = create_access_token(user.id)
    response = client.post(
        "/profile/refresh-key",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "refreshed" in response.json()["message"].lower()


def test_refresh_key_fails_when_no_free_vms(client, db_session):
    """Если у юзера нет назначенной VM и в пуле тоже нет свободных → 503."""
    user = _make_user(db_session, email="nofreevm-refresh@test.com")
    token = create_access_token(user.id)

    response = client.post(
        "/profile/refresh-key",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "busy" in response.json()["detail"].lower()


def test_refresh_key_works_when_user_already_has_vm(client, db_session):
    """Если у юзера уже назначена VM, refresh-key должен срабатывать
    даже если в пуле больше свободных нет — он может переактивировать ту же VM."""
    user = _make_user(db_session, email="hasvm@test.com")
    db_session.add(
        VirtualMachine(
            name="vm-mine",
            host="10.0.0.2",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=True,
            current_user_id=user.id,
            last_used_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    token = create_access_token(user.id)
    response = client.post(
        "/profile/refresh-key",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

def test_profile_does_not_expose_activation_key(client, db_session):
    """GET /profile никогда не должен возвращать сам ключ — только факт его наличия."""
    user = User(
        email="leaktest@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
        activation_key="super-secret-key-must-not-leak",
        activation_key_expires=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id)
    response = client.get("/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert "activation_key" not in body          # поле удалено
    assert body["has_pending_activation_key"] is True
    # И на всякий случай — сам ключ не появился ни в одной строке
    assert "super-secret-key-must-not-leak" not in response.text
