from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Admin


def seed_admin(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return

    existing_admin = db.scalar(select(Admin).where(Admin.email == settings.admin_email))
    if existing_admin is not None:
        return

    admin = Admin(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password.get_secret_value()),
    )
    db.add(admin)
    db.commit()
