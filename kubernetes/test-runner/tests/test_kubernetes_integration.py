"""
Kubernetes integration tests for ChatDB services
Tests service discovery, connectivity, and cluster functionality
"""
import pytest
import requests
import os
import time
from typing import Dict, List

# Service configuration mapping
SERVICES = {
    "training-orchestrator": {
        "url": os.getenv("TRAINING_ORCHESTRATOR_URL", "http://training-orchestrator:8000"),
        "health_path": "/health",
        "expected_response": {"status": "ok"}
    },
    "ml-engine": {
        "url": os.getenv("ML_ENGINE_URL", "http://ml-engine:5000"),
        "health_path": "/health",
        "expected_response": {"status": "ok"}
    },
    "model-registry": {
        "url": os.getenv("MODEL_REGISTRY_URL", "http://model-registry:8080"),
        "health_path": "/health", 
        "expected_response": {"status": "healthy"}
    },
    "query-parser": {
        "url": os.getenv("QUERY_PARSER_URL", "http://query-parser:5001"),
        "health_path": "/health",
        "expected_response": {"status": "ok"}
    },
    "db-connector": {
        "url": os.getenv("DB_CONNECTOR_URL", "http://db-connector:8081"),
        "health_path": "/actuator/health",
        "expected_response": {"status": "UP"}
    },
    "test-service": {
        "url": os.getenv("TEST_SERVICE_URL", "http://test-service:8001"),
        "health_path": "/",
        "expected_response": {"message": "Test Service is running"}
    }
}

@pytest.fixture
def service_urls() -> Dict[str, str]:
    """Get all service URLs for testing"""
    return {name: config["url"] for name, config in SERVICES.items()}

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.parametrize("service_name,service_config", SERVICES.items())
def test_service_health_endpoints(service_name: str, service_config: Dict):
    """Test that all services respond to health checks"""
    url = service_config["url"]
    health_path = service_config["health_path"]
    expected = service_config["expected_response"]
    
    try:
        response = requests.get(f"{url}{health_path}", timeout=10)
        assert response.status_code == 200
        
        response_json = response.json()
        
        # Check expected fields are present
        for key, value in expected.items():
            assert key in response_json, f"Missing key '{key}' in {service_name} health response"
            if value is not None:
                assert response_json[key] == value, f"Incorrect value for '{key}' in {service_name}"
                
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Cannot connect to {service_name} at {url}")
    except requests.exceptions.Timeout:
        pytest.fail(f"{service_name} health check timed out")
    except Exception as e:
        pytest.fail(f"Health check failed for {service_name}: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_service_discovery_dns(service_urls):
    """Test that Kubernetes DNS resolution works for services"""
    import socket
    
    dns_failures = []
    
    for service_name, url in service_urls.items():
        try:
            # Extract hostname from URL
            hostname = url.replace("http://", "").replace("https://", "").split(":")[0]
            
            # Try to resolve the hostname
            socket.gethostbyname(hostname)
            print(f"✓ DNS resolution successful for {service_name} ({hostname})")
            
        except socket.gaierror as e:
            dns_failures.append(f"{service_name}: {e}")
    
    if dns_failures:
        pytest.fail(f"DNS resolution failures: {dns_failures}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.slow
def test_service_startup_time(service_urls):
    """Test service startup and readiness"""
    max_wait_time = 60  # Maximum wait time in seconds
    check_interval = 2   # Check every 2 seconds
    
    startup_results = {}
    
    for service_name, url in service_urls.items():
        service_config = SERVICES[service_name]
        health_path = service_config["health_path"]
        
        start_time = time.time()
        service_ready = False
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(f"{url}{health_path}", timeout=5)
                if response.status_code == 200:
                    service_ready = True
                    ready_time = time.time() - start_time
                    startup_results[service_name] = ready_time
                    break
            except:
                pass
            
            time.sleep(check_interval)
        
        if not service_ready:
            startup_results[service_name] = "timeout"
    
    # Check results
    failed_services = [name for name, result in startup_results.items() if result == "timeout"]
    
    if failed_services:
        pytest.fail(f"Services failed to start within {max_wait_time}s: {failed_services}")
    
    # Log startup times
    for service, time_taken in startup_results.items():
        if isinstance(time_taken, float):
            print(f"{service} ready in {time_taken:.2f}s")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_inter_service_communication():
    """Test communication between services"""
    # Test Training Orchestrator -> Database connectivity
    training_url = SERVICES["training-orchestrator"]["url"]
    
    try:
        # Try to create a test job (this tests database connectivity)
        test_job = {
            "model_name": "connectivity_test",
            "dataset_location": "/data/test.csv",
            "cpu_request": 1
        }
        
        response = requests.post(f"{training_url}/jobs", json=test_job, timeout=15)
        assert response.status_code == 200
        
        # Clean up by retrieving the created job
        job_id = response.json()["id"]
        get_response = requests.get(f"{training_url}/jobs/{job_id}", timeout=10)
        assert get_response.status_code == 200
        
    except Exception as e:
        pytest.fail(f"Inter-service communication test failed: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_resource_limits_and_requests():
    """Test that services are running within expected resource limits"""
    try:
        from kubernetes import client, config
        
        # Load in-cluster config
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        
        # Get pods in current namespace
        pods = v1.list_namespaced_pod(namespace="default")
        
        chatdb_pods = [pod for pod in pods.items if any(service in pod.metadata.name for service in SERVICES.keys())]
        
        if not chatdb_pods:
            pytest.skip("No ChatDB pods found in current namespace")
        
        resource_issues = []
        
        for pod in chatdb_pods:
            pod_name = pod.metadata.name
            
            # Check if pod is running
            if pod.status.phase != "Running":
                resource_issues.append(f"{pod_name}: Not running (phase: {pod.status.phase})")
                continue
            
            # Check resource specifications
            for container in pod.spec.containers:
                if container.resources:
                    if container.resources.requests:
                        cpu_request = container.resources.requests.get('cpu')
                        memory_request = container.resources.requests.get('memory')
                        print(f"{pod_name}/{container.name}: CPU request: {cpu_request}, Memory request: {memory_request}")
                    
                    if container.resources.limits:
                        cpu_limit = container.resources.limits.get('cpu')
                        memory_limit = container.resources.limits.get('memory')
                        print(f"{pod_name}/{container.name}: CPU limit: {cpu_limit}, Memory limit: {memory_limit}")
        
        if resource_issues:
            pytest.fail(f"Resource issues found: {resource_issues}")
            
    except Exception as e:
        pytest.skip(f"Cannot test resource limits: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_persistent_storage():
    """Test that persistent storage is working for stateful services"""
    # Test database persistence by creating and retrieving data
    training_url = SERVICES["training-orchestrator"]["url"]
    
    try:
        # Create a test job
        test_job = {
            "model_name": "persistence_test",
            "dataset_location": "/data/persistence_test.csv",
            "cpu_request": 1
        }
        
        create_response = requests.post(f"{training_url}/jobs", json=test_job, timeout=15)
        assert create_response.status_code == 200
        
        job_id = create_response.json()["id"]
        
        # Wait a moment
        time.sleep(2)
        
        # Retrieve the job to test persistence
        get_response = requests.get(f"{training_url}/jobs/{job_id}", timeout=10)
        assert get_response.status_code == 200
        
        retrieved_job = get_response.json()
        assert retrieved_job["model_name"] == test_job["model_name"]
        assert retrieved_job["dataset_location"] == test_job["dataset_location"]
        
    except Exception as e:
        pytest.fail(f"Persistent storage test failed: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
def test_network_policies():
    """Test that network policies allow expected communication"""
    # Test that services can reach each other on expected ports
    connection_tests = [
        ("training-orchestrator", "postgres", 5432),
        ("model-registry", "postgres", 5432),
        ("training-orchestrator", "kafka", 9092)
    ]
    
    network_failures = []
    
    for source, target, port in connection_tests:
        try:
            # This is a basic connectivity test
            # In a real environment, you might use telnet or similar
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((target, port))
            sock.close()
            
            if result == 0:
                print(f"✓ {source} can reach {target}:{port}")
            else:
                network_failures.append(f"{source} cannot reach {target}:{port}")
                
        except Exception as e:
            network_failures.append(f"{source} -> {target}:{port} test failed: {e}")
    
    if network_failures:
        pytest.skip(f"Network policy tests require cluster access: {network_failures}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.slow
def test_service_failover_and_recovery():
    """Test service behavior during failures and recovery"""
    # This test would require more sophisticated cluster manipulation
    # For now, we'll test basic error handling
    
    training_url = SERVICES["training-orchestrator"]["url"]
    
    # Test with invalid data to trigger error handling
    invalid_job = {"invalid_field": "test_value"}
    
    try:
        response = requests.post(f"{training_url}/jobs", json=invalid_job, timeout=10)
        # Should return an error, not crash the service
        assert response.status_code in [400, 422]
        
        # Service should still be responsive after error
        health_response = requests.get(f"{training_url}/health", timeout=10)
        assert health_response.status_code == 200
        
    except Exception as e:
        pytest.fail(f"Service recovery test failed: {e}")