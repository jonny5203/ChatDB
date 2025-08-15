import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db
from models import Base, TrainingJob, JobStatus
from unittest.mock import patch, MagicMock

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@patch('main.producer')
def test_create_training_job(mock_producer, db_session):
    job_data = {"model_name": "test_model", "dataset_location": "/data/test.csv", "cpu_request": 2}
    response = client.post("/jobs", json=job_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["model_name"] == job_data["model_name"]
    assert data["dataset_location"] == job_data["dataset_location"]
    assert data["status"] == "pending"
    assert data["cpu_request"] == 2
    mock_producer.send.assert_called_once()

    db_job = db_session.query(TrainingJob).filter(TrainingJob.id == data["id"]).first()
    assert db_job is not None
    assert db_job.cpu_request == 2

def test_get_training_job(db_session):
    job = TrainingJob(id="test_job_id", model_name="test_model", dataset_location="/data/test.csv", status=JobStatus.completed, cpu_request=4)
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job.id
    assert data["cpu_request"] == 4

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch('main.threading.Thread')
@patch('main.time.sleep', return_value=None)
def test_consume_messages(mock_sleep, mock_thread, db_session):
    # This is a simplified test to check if the consumer logic is triggered
    # A more comprehensive test would require a running Kafka instance or a more sophisticated mocking library
    from main import consume_messages
    
    mock_consumer = MagicMock()
    mock_consumer.__iter__.return_value = [MagicMock(value={
        'job_id': 'test_job_id',
        'cpu_request': 1
    })]

    with patch('main.consumer', mock_consumer):
        consume_messages()
        mock_thread.assert_called_once()
