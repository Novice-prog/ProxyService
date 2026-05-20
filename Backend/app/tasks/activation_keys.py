from datetime import UTC, datetime, timedelta

from app.core.security import generate_activation_key
from app.db.models import User 

from sqlalchemy.orm import Session


def issue_activation_key(
    *,
    db: Session,
    user: User,
    expires_in_days: int = 7,
) -> str:
    activation_key = generate_activation_key()

    user.activation_key = activation_key
    user.activation_key_expires = datetime.now(UTC) + timedelta(days = expires_in_days)

    db.add(user)

    return activation_key