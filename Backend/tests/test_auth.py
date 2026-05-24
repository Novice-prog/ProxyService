from app.core.security import hash_password
from app.db.models import Admin, ProxyProtocol, User, VirtualMachine


def _add_free_vm(db_session, *, host: str = "10.0.0.1", port: int = 1080) -> VirtualMachine:
    """Хелпер: добавляет одну свободную VM в БД, чтобы register не падал в 503."""
    vm = VirtualMachine(
        name=f"vm-{host}-{port}",
        host=host,
        port=port,
        protocol=ProxyProtocol.SOCKS,
        is_active=True,
        current_user_id=None,
    )
    db_session.add(vm)
    db_session.commit()
    return vm


def test_register_success(client, db_session):
    _add_free_vm(db_session)

    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "password123",
            "password_confirm": "password123",
        },
    )

    assert response.status_code == 201
    assert "registered successfully" in response.json()["message"]


def test_register_password_mismatch(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "user@test.com",
            "password": "password123",
            "password_confirm": "otherpassword",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Password do not match"


def test_register_duplicate_email(client, db_session):
    _add_free_vm(db_session)

    payload = {
        "email": "duplicate@test.com",
        "password": "password123",
        "password_confirm": "password123",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]


def test_register_fails_when_no_free_vms(client, db_session):
    """Регистрация должна возвращать 503, если в пуле нет свободных VM.

    Юзер при этом НЕ должен создаваться в БД — иначе при повторной попытке
    «email уже зарегистрирован» перекроет реальную причину.
    """
    response = client.post(
        "/auth/register",
        json={
            "email": "nofreevm@test.com",
            "password": "password123",
            "password_confirm": "password123",
        },
    )

    assert response.status_code == 503
    assert "busy" in response.json()["detail"].lower()

    # Юзер не должен был сохраниться
    from sqlalchemy import select
    user = db_session.scalar(select(User).where(User.email == "nofreevm@test.com"))
    assert user is None


def test_register_fails_when_all_vms_occupied(client, db_session):
    """Активные VM есть, но все заняты другими юзерами → тоже 503."""
    other = User(
        email="busy_owner@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    db_session.add(
        VirtualMachine(
            name="vm-busy",
            host="10.0.0.99",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=True,
            current_user_id=other.id,
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/register",
        json={
            "email": "anotheruser@test.com",
            "password": "password123",
            "password_confirm": "password123",
        },
    )

    assert response.status_code == 503


def test_register_ignores_inactive_vms(client, db_session):
    """Деактивированные админом VM не считаются «свободными»."""
    db_session.add(
        VirtualMachine(
            name="vm-inactive",
            host="10.0.0.50",
            port=1080,
            protocol=ProxyProtocol.SOCKS,
            is_active=False,
            current_user_id=None,
        )
    )
    db_session.commit()

    response = client.post(
        "/auth/register",
        json={
            "email": "inactivevm@test.com",
            "password": "password123",
            "password_confirm": "password123",
        },
    )

    assert response.status_code == 503


def test_login_success(client, db_session):
    user = User(
        email="login@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "login@test.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, db_session):
    user = User(
        email="wrongpass@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "wrongpass@test.com", "password": "badpassword1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_refresh_token(client, db_session):
    user = User(
        email="refresh@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={"email": "refresh@test.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_admin_login(client, db_session):
    admin = Admin(
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/auth/admin/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
