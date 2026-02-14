import pytest
from fastapi.testclient import TestClient
from fastapi_pagination import add_pagination
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import os
import sys

# Ensure project root is on PYTHONPATH so `app` package imports work when running pytest
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app
from db.database import Base, get_db

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Get database session for tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    """Get TestClient with overridden database dependency and pagination"""
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    add_pagination(app)
    yield TestClient(app)
    app.dependency_overrides.clear()
