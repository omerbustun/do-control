import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from console.database import Base
from console.api.models import db_models  # Import all models

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture
def test_db():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)