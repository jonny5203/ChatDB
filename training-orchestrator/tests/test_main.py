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

@patch('main.kafka_producer')
def test_create_training_job(mock_kafka_producer, db_session):
    job_data = {"model_name": "test_model", "dataset_location": "/data/test.csv", "cpu_request": 2}
    response = client.post("/jobs", json=job_data)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["model_name"] == job_data["model_name"]
    assert data["dataset_location"] == job_data["dataset_location"]
    assert data["status"] == "pending"
    assert data["cpu_request"] == 2
    mock_kafka_producer.send.assert_called_once()

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

def test_list_training_jobs(db_session):
    # Create multiple test jobs
    job1 = TrainingJob(id="test_job_1", model_name="model_1", dataset_location="/data/test1.csv", status=JobStatus.pending, cpu_request=2)
    job2 = TrainingJob(id="test_job_2", model_name="model_2", dataset_location="/data/test2.csv", status=JobStatus.completed, cpu_request=4)
    db_session.add(job1)
    db_session.add(job2)
    db_session.commit()

    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    
    # Check that our jobs are in the list
    job_ids = [job["id"] for job in data]
    assert "test_job_1" in job_ids
    assert "test_job_2" in job_ids

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert "status" in health_data
    # Health can be "ok" or "degraded" depending on database connectivity
    assert health_data["status"] in ["ok", "degraded"]

def test_consume_messages_function_exists():
    # Simple test to verify the consume_messages function exists
    from main import consume_messages
    assert callable(consume_messages)
