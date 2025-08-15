import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from database import engine
from models.metadata import Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from services.metadata_service import MetadataService
from routers.metadata_router import get_db

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_engine():
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

@pytest.fixture(scope="session")
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session(test_engine, tables):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    del app.dependency_overrides[get_db]

@pytest.fixture
def metadata_service(db_session):
    return MetadataService(db_session)
