"""
Test configuration and fixtures for Training Orchestrator tests.
"""

import pytest
import psycopg2
import os
from typing import Dict, Any


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", 
        "kubernetes: marks tests as requiring Kubernetes environment"
    )
    config.addinivalue_line(
        "markers", 
        "slow: marks tests as slow running"
    )


@pytest.fixture(scope="session")
def database_config() -> Dict[str, Any]:
    """Database configuration for testing."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'postgres.default.svc.cluster.local'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'password'),
        'database': os.getenv('POSTGRES_DB', 'training_db')
    }


@pytest.fixture(scope="session")
def kafka_config() -> Dict[str, Any]:
    """Kafka configuration for testing."""
    return {
        'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka.default.svc.cluster.local:9092'),
        'topic': 'training_jobs'
    }


@pytest.fixture(scope="session")
def service_url() -> str:
    """Training Orchestrator service URL."""
    return os.getenv(
        'TRAINING_ORCHESTRATOR_URL', 
        'http://training-orchestrator.default.svc.cluster.local:8000'
    )


@pytest.fixture(scope="function")
def cleanup_jobs():
    """Fixture to track and cleanup test jobs."""
    job_ids = []
    
    def add_job(job_id: str):
        job_ids.append(job_id)
    
    yield add_job
    
    # Cleanup after test
    if job_ids:
        try:
            database_config_dict = {
                'host': os.getenv('POSTGRES_HOST', 'postgres.default.svc.cluster.local'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'password'),
                'database': os.getenv('POSTGRES_DB', 'training_db')
            }
            
            connection = psycopg2.connect(**database_config_dict)
            cursor = connection.cursor()
            
            for job_id in job_ids:
                cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass  # Best effort cleanup


@pytest.fixture(scope="session")
def check_kubernetes_environment():
    """Check if running in Kubernetes environment and skip tests if not available."""
    try:
        # Try to connect to expected Kubernetes service
        import requests
        service_url = os.getenv(
            'TRAINING_ORCHESTRATOR_URL', 
            'http://training-orchestrator.default.svc.cluster.local:8000'
        )
        response = requests.get(f"{service_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("Kubernetes environment not available or service not responding")
    except Exception:
        pytest.skip("Kubernetes environment not available")


@pytest.fixture(scope="session")
def check_database_connectivity():
    """Check database connectivity and skip tests if not available."""
    try:
        database_config_dict = {
            'host': os.getenv('POSTGRES_HOST', 'postgres.default.svc.cluster.local'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password'),
            'database': os.getenv('POSTGRES_DB', 'training_db')
        }
        
        connection = psycopg2.connect(**database_config_dict)
        connection.close()
    except Exception:
        pytest.skip("Database not available for testing")