from app.core.security import hash_password
from app.db.models import Admin, User


def test_register_success(client):
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


def test_register_duplicate_email(client):
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
