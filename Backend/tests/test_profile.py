from app.core.security import create_access_token, hash_password
from app.db.models import User


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
