from app.core.security import (
    create_access_token,
    get_token_subject,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    password = "MyPassword123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_has_user_id():
    token = create_access_token(42)

    subject = get_token_subject(token, expected_type="access")

    assert subject == "42"
