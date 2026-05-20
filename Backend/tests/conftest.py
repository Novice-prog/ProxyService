import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# важно задать env до импорта app
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-pytest")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RATE_LIMIT_ENABLED"] = "false"

from app.core.config import get_settings
from app.db.deps import get_db
from app.db.models import Model
from app.main import app

get_settings.cache_clear()

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def prepare_database():
    Model.metadata.drop_all(bind=TEST_ENGINE)
    Model.metadata.create_all(bind=TEST_ENGINE)
    yield
    Model.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.routers.auth.send_activation_key.delay"), patch(
        "app.routers.profile.send_activation_key.delay"
    ):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()
