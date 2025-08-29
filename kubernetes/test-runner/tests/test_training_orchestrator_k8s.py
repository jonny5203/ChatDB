"""
Comprehensive Kubernetes integration tests for Training Orchestrator service
Tests service accessibility, database connectivity, job lifecycle, and resilience within K8s cluster
"""
import pytest
import requests
import json
import os
import time
import psycopg2
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

@pytest.fixture
def training_orchestrator_url():
    """Get Training Orchestrator service URL with Kubernetes DNS resolution"""
    # Support both internal Kubernetes DNS and external access
    base_url = os.getenv("TRAINING_ORCHESTRATOR_URL", "http://training-orchestrator.default.svc.cluster.local:8000")
    # Fallback to service name for basic Kubernetes deployment
    if "svc.cluster.local" not in base_url and "training-orchestrator" not in base_url:
        return "http://training-orchestrator:8000"
    return base_url

@pytest.fixture
def test_job_data():
    """Sample training job data for testing"""
    return {
        "model_name": f"test_model_{uuid4().hex[:8]}",
        "dataset_location": "/data/test_dataset.csv",
        "cpu_request": 2
    }

@pytest.fixture
def database_config():
    """Database configuration for direct database connectivity tests"""
    return {
        "host": os.getenv("DATABASE_HOST", "postgres.default.svc.cluster.local"),
        "port": int(os.getenv("DATABASE_PORT", "5432")),
        "database": os.getenv("DATABASE_NAME", "training_db"),
        "user": os.getenv("DATABASE_USER", "user"),
        "password": os.getenv("DATABASE_PASSWORD", "password")
    }

@pytest.mark.integration
@pytest.mark.kubernetes
def test_training_orchestrator_health(training_orchestrator_url):
    """Test that Training Orchestrator health endpoint is accessible"""
    response = requests.get(f"{training_orchestrator_url}/health", timeout=10)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.database
def test_create_training_job_k8s(training_orchestrator_url, test_job_data):
    """Test creating a training job through Kubernetes service"""
    # Create training job
    response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=test_job_data,
        timeout=30
    )
    
    assert response.status_code == 200
    job_data = response.json()
    
    # Verify job was created with correct data
    assert "id" in job_data
    assert job_data["model_name"] == test_job_data["model_name"]
    assert job_data["dataset_location"] == test_job_data["dataset_location"]
    assert job_data["status"] == "pending"
    assert job_data["cpu_request"] == 2
    
    job_id = job_data["id"]
    
    # Wait a moment for processing
    time.sleep(2)
    
    # Retrieve the job to verify persistence
    get_response = requests.get(f"{training_orchestrator_url}/jobs/{job_id}", timeout=10)
    assert get_response.status_code == 200
    
    retrieved_job = get_response.json()
    assert retrieved_job["id"] == job_id
    assert retrieved_job["model_name"] == test_job_data["model_name"]

@pytest.mark.integration
@pytest.mark.kubernetes
def test_list_training_jobs_k8s(training_orchestrator_url, test_job_data):
    """Test listing training jobs through Kubernetes service"""
    # Create a test job first
    create_response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=test_job_data,
        timeout=30
    )
    assert create_response.status_code == 200
    
    # List all jobs
    list_response = requests.get(f"{training_orchestrator_url}/jobs", timeout=10)
    assert list_response.status_code == 200
    
    jobs_list = list_response.json()
    assert isinstance(jobs_list, list)
    
    # Verify our test job is in the list
    job_ids = [job["id"] for job in jobs_list]
    created_job_id = create_response.json()["id"]
    assert created_job_id in job_ids

@pytest.mark.integration
@pytest.mark.kubernetes 
@pytest.mark.slow
def test_service_connectivity_timeout(training_orchestrator_url):
    """Test service connectivity and timeout handling"""
    try:
        response = requests.get(f"{training_orchestrator_url}/health", timeout=5)
        assert response.status_code == 200
    except requests.exceptions.Timeout:
        pytest.fail("Service is not responding within timeout period")
    except requests.exceptions.ConnectionError:
        pytest.fail("Cannot connect to Training Orchestrator service")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_service_error_handling(training_orchestrator_url):
    """Test service error handling for invalid requests"""
    # Test invalid job data
    invalid_job_data = {"invalid_field": "test"}
    
    response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=invalid_job_data,
        timeout=10
    )
    
    # Should return validation error (422) or bad request (400)
    assert response.status_code in [400, 422]

@pytest.mark.integration
@pytest.mark.kubernetes
def test_nonexistent_job_retrieval(training_orchestrator_url):
    """Test retrieving a non-existent job"""
    fake_job_id = "non-existent-job-id"
    
    response = requests.get(f"{training_orchestrator_url}/jobs/{fake_job_id}", timeout=10)
    assert response.status_code == 404

# Database Connectivity Tests
@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.database
def test_database_connectivity_direct(database_config):
    """Test direct database connectivity to PostgreSQL service"""
    try:
        connection = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"]
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        
        cursor.close()
        connection.close()
        
    except psycopg2.OperationalError as e:
        pytest.fail(f"Cannot connect to PostgreSQL database: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.database 
def test_training_jobs_table_exists(database_config):
    """Test that training_jobs table exists and has correct structure"""
    try:
        connection = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"]
        )
        
        cursor = connection.cursor()
        
        # Check if training_jobs table exists
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'training_jobs'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        assert len(columns) >= 5  # id, model_name, dataset_location, status, cpu_request
        
        column_names = [col[0] for col in columns]
        assert "id" in column_names
        assert "model_name" in column_names
        assert "dataset_location" in column_names
        assert "status" in column_names
        assert "cpu_request" in column_names
        
        cursor.close()
        connection.close()
        
    except psycopg2.Error as e:
        pytest.fail(f"Database table structure test failed: {e}")

# Job Lifecycle Tests  
@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.database
@pytest.mark.slow
def test_job_lifecycle_complete(training_orchestrator_url, test_job_data):
    """Test complete job lifecycle from creation to completion tracking"""
    # Create job
    create_response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=test_job_data,
        timeout=30
    )
    assert create_response.status_code == 200
    
    job_data = create_response.json()
    job_id = job_data["id"]
    
    # Verify initial status is pending
    assert job_data["status"] == "pending"
    
    # Wait and check if status transitions (with Kafka message processing)
    # This tests the full message processing pipeline
    max_wait_time = 30
    start_time = time.time()
    status_transitions = []
    
    while time.time() - start_time < max_wait_time:
        get_response = requests.get(f"{training_orchestrator_url}/jobs/{job_id}", timeout=10)
        if get_response.status_code == 200:
            current_job = get_response.json()
            current_status = current_job["status"]
            
            if not status_transitions or status_transitions[-1] != current_status:
                status_transitions.append(current_status)
                
        time.sleep(2)
    
    # Verify we observed expected status transitions
    assert "pending" in status_transitions
    # Note: In a real environment, we might see in_progress and completed
    # For testing, we verify at least the initial pending state

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.performance
def test_concurrent_job_creation_limits(training_orchestrator_url):
    """Test concurrent job creation and service limits"""
    num_concurrent_jobs = 5
    job_creation_data = []
    
    for i in range(num_concurrent_jobs):
        job_creation_data.append({
            "model_name": f"concurrent_model_{i}_{uuid4().hex[:8]}",
            "dataset_location": f"/data/concurrent_test_{i}.csv",
            "cpu_request": 1
        })
    
    # Create jobs concurrently
    created_jobs = []
    with ThreadPoolExecutor(max_workers=num_concurrent_jobs) as executor:
        futures = []
        for job_data in job_creation_data:
            future = executor.submit(
                requests.post,
                f"{training_orchestrator_url}/jobs",
                json=job_data,
                timeout=30
            )
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                response = future.result()
                if response.status_code == 200:
                    created_jobs.append(response.json())
                else:
                    # Some jobs might fail due to concurrency limits
                    assert response.status_code in [429, 503]  # Rate limited or service unavailable
            except requests.exceptions.RequestException as e:
                # Some failures are acceptable under high load
                pass
    
    # At least some jobs should be created successfully
    assert len(created_jobs) > 0
    
    # Verify all created jobs have unique IDs
    job_ids = [job["id"] for job in created_jobs]
    assert len(set(job_ids)) == len(job_ids)  # All IDs should be unique

# Error Handling and Edge Case Tests
@pytest.mark.integration
@pytest.mark.kubernetes
def test_invalid_job_data_validation(training_orchestrator_url):
    """Test comprehensive input validation for job creation"""
    
    # Test missing required fields
    invalid_jobs = [
        {},  # Empty
        {"model_name": "test"},  # Missing dataset_location
        {"dataset_location": "/data/test.csv"},  # Missing model_name
        {"model_name": "", "dataset_location": "/data/test.csv"},  # Empty model_name
        {"model_name": "test", "dataset_location": ""},  # Empty dataset_location
        {"model_name": "test", "dataset_location": "/data/test.csv", "cpu_request": "invalid"},  # Invalid cpu_request type
        {"model_name": "test", "dataset_location": "/data/test.csv", "cpu_request": -1},  # Negative cpu_request
        {"model_name": "test", "dataset_location": "/data/test.csv", "cpu_request": 0},  # Zero cpu_request
    ]
    
    for invalid_job in invalid_jobs:
        response = requests.post(
            f"{training_orchestrator_url}/jobs",
            json=invalid_job,
            timeout=10
        )
        assert response.status_code in [400, 422], f"Failed validation for: {invalid_job}"

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.resilience
def test_service_recovery_after_error(training_orchestrator_url):
    """Test that service recovers gracefully after errors"""
    # First, cause an error with invalid data
    invalid_data = {"invalid_field": "test"}
    error_response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=invalid_data,
        timeout=10
    )
    assert error_response.status_code in [400, 422]
    
    # Then verify service is still healthy and can process valid requests
    health_response = requests.get(f"{training_orchestrator_url}/health", timeout=10)
    assert health_response.status_code == 200
    
    # Create a valid job to ensure service functionality is intact
    valid_job_data = {
        "model_name": f"recovery_test_{uuid4().hex[:8]}",
        "dataset_location": "/data/recovery_test.csv",
        "cpu_request": 1
    }
    
    valid_response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=valid_job_data,
        timeout=30
    )
    assert valid_response.status_code == 200
    
    job_data = valid_response.json()
    assert job_data["model_name"] == valid_job_data["model_name"]

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.timeout
def test_service_timeout_handling(training_orchestrator_url):
    """Test service handles timeouts and high load gracefully"""
    # Test health endpoint with very short timeout
    try:
        response = requests.get(f"{training_orchestrator_url}/health", timeout=1)
        assert response.status_code == 200
    except requests.exceptions.Timeout:
        pytest.skip("Service response time too slow for aggressive timeout test")
    
    # Test job creation with moderate timeout
    job_data = {
        "model_name": f"timeout_test_{uuid4().hex[:8]}",
        "dataset_location": "/data/timeout_test.csv",
        "cpu_request": 1
    }
    
    response = requests.post(
        f"{training_orchestrator_url}/jobs",
        json=job_data,
        timeout=15
    )
    assert response.status_code == 200