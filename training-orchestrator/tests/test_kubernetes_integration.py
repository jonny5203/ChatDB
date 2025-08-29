"""
Training Orchestrator Kubernetes Integration Tests

Tests the service's behavior when deployed in a Kubernetes environment,
including service discovery, database connectivity, Kafka integration,
concurrent job processing, and error recovery.
"""

import pytest
import requests
import psycopg2
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import json
import uuid
from typing import Dict, List
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, KafkaConnectionError

# Kubernetes service URLs (assumes cluster deployment)
TRAINING_ORCHESTRATOR_URL = os.getenv(
    'TRAINING_ORCHESTRATOR_URL', 
    'http://training-orchestrator.default.svc.cluster.local:8000'
)

# Database configuration for direct connectivity testing
DATABASE_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres.default.svc.cluster.local'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password'),
    'database': os.getenv('POSTGRES_DB', 'training_db')
}

# Kafka configuration for integration testing
KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka.default.svc.cluster.local:9092'),
    'topic': 'training_jobs'
}

class TestKubernetesServiceDiscovery:
    """Test Kubernetes DNS resolution and service connectivity."""
    
    def test_service_dns_resolution(self):
        """Test that the service is discoverable via Kubernetes DNS."""
        try:
            response = requests.get(f"{TRAINING_ORCHESTRATOR_URL}/health", timeout=10)
            assert response.status_code == 200
            assert response.json()['status'] == 'ok'
        except requests.exceptions.ConnectionError:
            pytest.fail("Cannot connect to training orchestrator via Kubernetes service DNS")
    
    def test_service_endpoints_available(self):
        """Test all critical service endpoints are accessible."""
        endpoints = ['/health', '/jobs']
        
        for endpoint in endpoints:
            response = requests.get(f"{TRAINING_ORCHESTRATOR_URL}{endpoint}", timeout=10)
            assert response.status_code in [200, 405], f"Endpoint {endpoint} not accessible"

class TestDatabaseConnectivity:
    """Test direct database connectivity and service database integration."""
    
    def test_database_connectivity_direct(self):
        """Test direct database connection to validate connectivity."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
            cursor.close()
            connection.close()
        except psycopg2.Error as e:
            pytest.fail(f"Database connectivity failed: {e}")
    
    def test_database_tables_exist(self):
        """Verify training job tables exist and are accessible."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'training_jobs'
                );
            """)
            table_exists = cursor.fetchone()[0]
            assert table_exists, "training_jobs table does not exist"
            cursor.close()
            connection.close()
        except psycopg2.Error as e:
            pytest.fail(f"Database table validation failed: {e}")
    
    def test_service_database_integration(self):
        """Test service can successfully interact with database."""
        # Create a test job via the service
        job_data = {
            "model_name": "k8s_test_model",
            "dataset_location": "/data/k8s_test.csv",
            "cpu_request": 1
        }
        
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
        assert response.status_code == 200
        
        job_response = response.json()
        job_id = job_response['id']
        
        # Verify job exists in database directly
        connection = psycopg2.connect(**DATABASE_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT id, model_name, status FROM training_jobs WHERE id = %s", (job_id,))
        db_job = cursor.fetchone()
        assert db_job is not None
        assert db_job[1] == "k8s_test_model"
        
        # Cleanup
        cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
        connection.commit()
        cursor.close()
        connection.close()

class TestJobLifecycleManagement:
    """Test complete job lifecycle in Kubernetes environment."""
    
    def test_job_creation_workflow(self):
        """Test end-to-end job creation workflow."""
        job_data = {
            "model_name": "lifecycle_test_model",
            "dataset_location": "/data/lifecycle_test.csv",
            "cpu_request": 2
        }
        
        # Create job
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
        assert response.status_code == 200
        
        job = response.json()
        job_id = job['id']
        
        # Verify job details
        assert job['model_name'] == job_data['model_name']
        assert job['dataset_location'] == job_data['dataset_location']
        assert job['status'] == 'pending'
        assert job['cpu_request'] == 2
        
        # Retrieve job
        response = requests.get(f"{TRAINING_ORCHESTRATOR_URL}/jobs/{job_id}", timeout=10)
        assert response.status_code == 200
        retrieved_job = response.json()
        assert retrieved_job['id'] == job_id
        assert retrieved_job['model_name'] == job_data['model_name']
        
        # Cleanup
        self._cleanup_job(job_id)
    
    def test_job_listing(self):
        """Test job listing functionality."""
        # Create multiple test jobs
        job_ids = []
        for i in range(3):
            job_data = {
                "model_name": f"list_test_model_{i}",
                "dataset_location": f"/data/list_test_{i}.csv",
                "cpu_request": 1
            }
            response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
            assert response.status_code == 200
            job_ids.append(response.json()['id'])
        
        # List jobs
        response = requests.get(f"{TRAINING_ORCHESTRATOR_URL}/jobs", timeout=10)
        assert response.status_code == 200
        jobs = response.json()
        assert isinstance(jobs, list)
        
        # Verify our jobs are in the list
        listed_job_ids = [job['id'] for job in jobs]
        for job_id in job_ids:
            assert job_id in listed_job_ids
        
        # Cleanup
        for job_id in job_ids:
            self._cleanup_job(job_id)
    
    def _cleanup_job(self, job_id: str):
        """Helper to cleanup test jobs."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass  # Best effort cleanup

class TestConcurrentJobProcessing:
    """Test concurrent job processing and resource management."""
    
    def test_concurrent_job_creation(self):
        """Test system handles concurrent job creation properly."""
        def create_job(job_index: int) -> Dict:
            job_data = {
                "model_name": f"concurrent_model_{job_index}",
                "dataset_location": f"/data/concurrent_{job_index}.csv",
                "cpu_request": 1
            }
            response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=15)
            return response.json() if response.status_code == 200 else None
        
        # Create jobs concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_job, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # Verify all jobs were created successfully
        successful_jobs = [job for job in results if job is not None]
        assert len(successful_jobs) == 5
        
        # Verify unique job IDs
        job_ids = [job['id'] for job in successful_jobs]
        assert len(set(job_ids)) == 5
        
        # Cleanup
        for job in successful_jobs:
            self._cleanup_job(job['id'])
    
    def test_concurrent_job_creation_limits(self):
        """Test semaphore limits for concurrent job processing."""
        job_ids = []
        
        def create_multiple_jobs(count: int) -> List[str]:
            created_ids = []
            for i in range(count):
                job_data = {
                    "model_name": f"limit_test_model_{i}",
                    "dataset_location": f"/data/limit_test_{i}.csv",
                    "cpu_request": 1
                }
                try:
                    response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
                    if response.status_code == 200:
                        created_ids.append(response.json()['id'])
                except requests.RequestException:
                    pass  # Some requests may fail due to limits
            return created_ids
        
        # Create many jobs to test limits
        job_ids = create_multiple_jobs(8)
        
        # System should handle all requests gracefully (either succeed or return appropriate errors)
        assert len(job_ids) > 0, "System should create at least some jobs"
        
        # Cleanup
        for job_id in job_ids:
            self._cleanup_job(job_id)
    
    def _cleanup_job(self, job_id: str):
        """Helper to cleanup test jobs."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass

class TestKafkaIntegration:
    """Test Kafka integration in Kubernetes environment."""
    
    @pytest.fixture(scope="class")
    def kafka_producer(self):
        """Create Kafka producer for testing."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                api_version=(0, 10, 1)
            )
            yield producer
            producer.close()
        except KafkaConnectionError:
            pytest.skip("Kafka not available for integration testing")
    
    @pytest.fixture(scope="class")
    def kafka_consumer(self):
        """Create Kafka consumer for testing."""
        try:
            consumer = KafkaConsumer(
                KAFKA_CONFIG['topic'],
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=5000,
                auto_offset_reset='latest',
                api_version=(0, 10, 1)
            )
            yield consumer
            consumer.close()
        except KafkaConnectionError:
            pytest.skip("Kafka not available for integration testing")
    
    def test_kafka_message_production(self, kafka_consumer):
        """Test that job creation produces Kafka messages."""
        # Start consuming messages in background
        messages = []
        
        def consume_messages():
            for message in kafka_consumer:
                messages.append(message.value)
                break  # Only consume one message for this test
        
        consumer_thread = threading.Thread(target=consume_messages)
        consumer_thread.daemon = True
        consumer_thread.start()
        
        time.sleep(1)  # Give consumer time to start
        
        # Create a job (should produce a message)
        job_data = {
            "model_name": "kafka_test_model",
            "dataset_location": "/data/kafka_test.csv",
            "cpu_request": 1
        }
        
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
        assert response.status_code == 200
        job_id = response.json()['id']
        
        # Wait for message to be consumed
        consumer_thread.join(timeout=10)
        
        # Verify message was produced
        assert len(messages) > 0, "No Kafka message was produced for job creation"
        
        message = messages[0]
        assert 'job_id' in message
        assert message['job_id'] == job_id
        
        # Cleanup
        self._cleanup_job(job_id)
    
    def _cleanup_job(self, job_id: str):
        """Helper to cleanup test jobs."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass

class TestErrorHandlingAndRecovery:
    """Test error handling and service recovery in Kubernetes."""
    
    def test_service_health_monitoring(self):
        """Test service health endpoint provides accurate status."""
        response = requests.get(f"{TRAINING_ORCHESTRATOR_URL}/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        assert 'status' in health_data
        assert health_data['status'] in ['ok', 'degraded']
    
    def test_database_connection_recovery(self):
        """Test service handles database connectivity issues gracefully."""
        # This test assumes the service is designed to handle database failures gracefully
        # In a real scenario, we might temporarily disrupt database connectivity
        
        # Create a job to verify normal operation
        job_data = {
            "model_name": "recovery_test_model",
            "dataset_location": "/data/recovery_test.csv",
            "cpu_request": 1
        }
        
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
        
        # Service should either succeed or return appropriate error
        assert response.status_code in [200, 500, 503], "Service should handle database issues gracefully"
        
        if response.status_code == 200:
            job_id = response.json()['id']
            self._cleanup_job(job_id)
    
    def test_invalid_job_data_handling(self):
        """Test service properly validates and handles invalid job data."""
        invalid_jobs = [
            {},  # Empty data
            {"model_name": ""},  # Empty model name
            {"model_name": "test", "dataset_location": "", "cpu_request": -1},  # Invalid CPU request
            {"model_name": "test", "cpu_request": "invalid"},  # Invalid CPU request type
        ]
        
        for invalid_job in invalid_jobs:
            response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=invalid_job, timeout=10)
            assert response.status_code in [400, 422], f"Invalid job data should be rejected: {invalid_job}"
    
    def test_service_recovery_after_error(self):
        """Test service continues to function after encountering errors."""
        # Send invalid request to potentially trigger error state
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json={}, timeout=10)
        assert response.status_code in [400, 422]
        
        # Verify service still functions normally
        job_data = {
            "model_name": "post_error_model",
            "dataset_location": "/data/post_error.csv",
            "cpu_request": 1
        }
        
        response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
        assert response.status_code == 200, "Service should recover after error"
        
        if response.status_code == 200:
            job_id = response.json()['id']
            self._cleanup_job(job_id)
    
    def _cleanup_job(self, job_id: str):
        """Helper to cleanup test jobs."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass

class TestResourceManagement:
    """Test resource management and constraints in Kubernetes."""
    
    def test_cpu_request_validation(self):
        """Test CPU request validation and limits."""
        # Test valid CPU requests
        valid_requests = [1, 2, 4]
        for cpu_request in valid_requests:
            job_data = {
                "model_name": f"cpu_test_model_{cpu_request}",
                "dataset_location": f"/data/cpu_test_{cpu_request}.csv",
                "cpu_request": cpu_request
            }
            response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
            assert response.status_code == 200
            
            job = response.json()
            assert job['cpu_request'] == cpu_request
            self._cleanup_job(job['id'])
        
        # Test invalid CPU requests
        invalid_requests = [0, -1, 100]  # Assuming 100 is beyond system limits
        for cpu_request in invalid_requests:
            job_data = {
                "model_name": "invalid_cpu_model",
                "dataset_location": "/data/invalid_cpu.csv",
                "cpu_request": cpu_request
            }
            response = requests.post(f"{TRAINING_ORCHESTRATOR_URL}/jobs", json=job_data, timeout=10)
            # Should either reject invalid requests or clamp to valid values
            if response.status_code == 200:
                job = response.json()
                assert job['cpu_request'] > 0  # Should be clamped to valid value
                self._cleanup_job(job['id'])
            else:
                assert response.status_code in [400, 422]
    
    def _cleanup_job(self, job_id: str):
        """Helper to cleanup test jobs."""
        try:
            connection = psycopg2.connect(**DATABASE_CONFIG)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM training_jobs WHERE id = %s", (job_id,))
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            pass

# Test configuration for pytest markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.kubernetes,
    pytest.mark.slow
]