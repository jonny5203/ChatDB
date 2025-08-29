# ChatDB Test Container Comprehensive Guide

## Overview

The ChatDB test container (`chatdb-test-runner:latest`) is a comprehensive testing solution designed to validate the entire microservices architecture within Kubernetes environments. It provides automated testing for service connectivity, data persistence, message queuing, and system integration.

## Container Architecture

### Base Configuration
- **Base Image**: `python:3.11-slim`
- **User**: Non-root (`testuser`) for security
- **Working Directory**: `/app`
- **Dependencies**: 30+ testing and integration libraries

### Environment Variables
```bash
# Service URLs (Kubernetes DNS)
TRAINING_ORCHESTRATOR_URL=http://training-orchestrator:8000
ML_ENGINE_URL=http://ml-engine:5000
MODEL_REGISTRY_URL=http://model-registry:8080
QUERY_PARSER_URL=http://query-parser:5001
DB_CONNECTOR_URL=http://db-connector:8081
TEST_SERVICE_URL=http://test-service:8001

# Infrastructure
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
DATABASE_URL=postgresql://postgres:password@postgres:5432/training_db
```

## Test Categories & Coverage

### 1. Service Health & Connectivity Tests

**File**: `test_kubernetes_integration.py`

**What it tests**:
- ✅ Service discovery via Kubernetes DNS
- ✅ Health endpoint responsiveness
- ✅ Service startup times and readiness
- ✅ Inter-service communication
- ✅ Resource limits and requests
- ✅ Network policies and connectivity
- ✅ Persistent storage functionality

**Test Functions**:
- `test_service_health_endpoints()` - Validates all service `/health` endpoints
- `test_service_discovery_dns()` - Verifies Kubernetes DNS resolution
- `test_service_startup_time()` - Measures service readiness (max 60s)
- `test_inter_service_communication()` - Tests cross-service API calls
- `test_resource_limits_and_requests()` - Validates Kubernetes resource specs
- `test_network_policies()` - Checks allowed/blocked connections
- `test_persistent_storage()` - Validates database persistence
- `test_service_failover_and_recovery()` - Tests error handling resilience

### 2. Training Orchestrator Integration Tests

**File**: `test_training_orchestrator_k8s.py`

**What it tests**:
- ✅ Training job lifecycle management
- ✅ Database integration and persistence
- ✅ API endpoint functionality
- ✅ Error handling and validation
- ✅ Timeout and connectivity resilience

**Test Functions**:
- `test_training_orchestrator_health()` - Service availability check
- `test_create_training_job_k8s()` - Job creation and persistence validation
- `test_list_training_jobs_k8s()` - Job listing and filtering
- `test_service_connectivity_timeout()` - Connection timeout handling
- `test_service_error_handling()` - Invalid request processing
- `test_nonexistent_job_retrieval()` - 404 error handling

**Test Data**:
```python
{
    "model_name": "test_model_12345678",
    "dataset_location": "/data/test_dataset.csv",
    "cpu_request": 2,
    "memory_request": "2Gi"
}
```

### 3. Kafka Message Queue Tests

**File**: `test_kafka_integration.py`

**What it tests**:
- ✅ Kafka cluster connectivity
- ✅ Message production and consumption
- ✅ Topic creation and management
- ✅ Message serialization/deserialization
- ✅ Error handling and resilience

**Test Functions**:
- `test_kafka_connectivity()` - Basic Kafka cluster connection
- `test_training_job_message_production()` - Produces training job messages
- `test_message_consumption()` - End-to-end message flow validation
- `test_kafka_topic_creation()` - Topic management capabilities
- `test_kafka_error_handling()` - Invalid operations and recovery

**Message Topics Tested**:
- `training-jobs` - Training job notifications
- `query-results` - Query processing results
- `model-updates` - Model registry updates

## Running Tests

### 1. Local Testing (Development)

```bash
# Build the container
cd kubernetes/test-runner
docker build -t chatdb-test-runner:latest .

# Run specific test categories
docker run --rm chatdb-test-runner:latest pytest tests/test_kubernetes_integration.py -v
docker run --rm chatdb-test-runner:latest pytest tests/test_training_orchestrator_k8s.py -v
docker run --rm chatdb-test-runner:latest pytest tests/test_kafka_integration.py -v

# Run all tests
docker run --rm chatdb-test-runner:latest pytest -v

# Run with specific markers
docker run --rm chatdb-test-runner:latest pytest -m "integration" -v
docker run --rm chatdb-test-runner:latest pytest -m "kubernetes" -v
docker run --rm chatdb-test-runner:latest pytest -m "kafka" -v
```

### 2. Kubernetes Job Deployment

**🚀 For complete Minikube deployment instructions, see:** [`docs/testing/minikube-deployment-guide.md`](./minikube-deployment-guide.md)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: chatdb-integration-tests
  namespace: chatdb-testing
spec:
  template:
    spec:
      containers:
      - name: test-runner
        image: chatdb-test-runner:latest
        imagePullPolicy: Never  # Use local image in Minikube
        command: ["pytest", "-v", "--tb=short", "./tests/"]
        env:
        - name: TRAINING_ORCHESTRATOR_URL
          value: "http://training-orchestrator.chatdb-services:8000"
        - name: ML_ENGINE_URL
          value: "http://ml-engine.chatdb-services:5000"
        - name: MODEL_REGISTRY_URL
          value: "http://model-registry.chatdb-services:8080"
        - name: QUERY_PARSER_URL
          value: "http://query-parser.chatdb-services:5001"
        - name: DB_CONNECTOR_URL
          value: "http://db-connector.chatdb-services:8081"
        - name: TEST_SERVICE_URL
          value: "http://test-service.chatdb-services:8001"
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka.chatdb-system:9092"
        - name: DATABASE_URL
          value: "postgresql://postgres:password@postgres.chatdb-system:5432/training_db"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
      restartPolicy: Never
  backoffLimit: 3
```

Deploy and monitor:
```bash
# Deploy test job
kubectl apply -f test-job.yaml

# Monitor progress
kubectl get jobs -n chatdb-testing
kubectl logs job/chatdb-integration-tests -n chatdb-testing -f

# Check results
kubectl describe job chatdb-integration-tests -n chatdb-testing
```

**Quick Minikube Setup:**
```bash
# 1. Start Minikube with adequate resources
minikube start --cpus=4 --memory=8192 --disk-size=20g

# 2. Build images in Minikube
eval $(minikube docker-env)
docker build -t chatdb-test-runner:latest kubernetes/test-runner/

# 3. Deploy ChatDB services (see deployment guide for details)
kubectl apply -f kubernetes/infrastructure/
kubectl apply -f kubernetes/services/

# 4. Run tests
kubectl apply -f test-job.yaml
```

### 3. Continuous Integration

```bash
# Automated testing pipeline
make test-integration    # Local Docker testing
make test-kubernetes     # Deploy to cluster and test
make test-robustness    # Extended resilience testing
```

## Test Markers and Categories

### Pytest Markers
- `@pytest.mark.integration` - Integration tests requiring running services
- `@pytest.mark.kubernetes` - Tests requiring Kubernetes environment
- `@pytest.mark.kafka` - Tests requiring Kafka cluster
- `@pytest.mark.database` - Tests requiring PostgreSQL database
- `@pytest.mark.slow` - Tests with longer execution time (>10s)
- `@pytest.mark.unit` - Fast unit tests

### Running Specific Categories
```bash
# Quick smoke tests
pytest -m "not slow" -v

# Integration tests only
pytest -m "integration and kubernetes" -v

# Infrastructure tests
pytest -m "kafka or database" -v

# Full comprehensive suite
pytest -v --tb=long
```

## Expected Test Results

### Healthy System Output
```
test_kubernetes_integration.py::test_service_health_endpoints[training-orchestrator] PASSED
test_kubernetes_integration.py::test_service_health_endpoints[ml-engine] PASSED
test_kubernetes_integration.py::test_service_health_endpoints[model-registry] PASSED
test_kubernetes_integration.py::test_service_health_endpoints[query-parser] PASSED
test_kubernetes_integration.py::test_service_health_endpoints[db-connector] PASSED
test_kubernetes_integration.py::test_service_health_endpoints[test-service] PASSED
test_kubernetes_integration.py::test_service_discovery_dns PASSED
test_kubernetes_integration.py::test_inter_service_communication PASSED

test_training_orchestrator_k8s.py::test_training_orchestrator_health PASSED
test_training_orchestrator_k8s.py::test_create_training_job_k8s PASSED
test_training_orchestrator_k8s.py::test_list_training_jobs_k8s PASSED

test_kafka_integration.py::test_kafka_connectivity PASSED
test_kafka_integration.py::test_training_job_message_production PASSED
test_kafka_integration.py::test_message_consumption PASSED

==================== 15 passed, 0 failed, 3 skipped ====================
```

### Common Failure Patterns

#### Service Not Ready
```
test_kubernetes_integration.py::test_service_health_endpoints[training-orchestrator] FAILED
E   ConnectionError: Cannot connect to training-orchestrator at http://training-orchestrator:8000
```
**Solution**: Wait for service deployment to complete, check pod status

#### Database Connection Issues
```
test_training_orchestrator_k8s.py::test_create_training_job_k8s FAILED
E   requests.exceptions.HTTPException: 500 Server Error
```
**Solution**: Verify PostgreSQL is running and accessible, check connection string

#### Kafka Not Available
```
test_kafka_integration.py::test_kafka_connectivity SKIPPED
Reason: Kafka not available: [Errno 111] Connection refused
```
**Solution**: Ensure Kafka cluster is deployed and accessible

## Performance Benchmarks

### Expected Execution Times
- **Service Health Checks**: 2-5 seconds per service
- **Database Operations**: 1-3 seconds per test
- **Kafka Tests**: 5-15 seconds (includes topic creation)
- **Full Test Suite**: 45-90 seconds

### Resource Requirements
- **CPU**: 0.1-0.5 cores during execution
- **Memory**: 128-256 MB RAM
- **Network**: Minimal bandwidth, low latency required
- **Storage**: Ephemeral only

## Troubleshooting Guide

### Container Won't Start
```bash
# Check image availability
docker images | grep chatdb-test-runner

# Inspect container
docker run --rm -it chatdb-test-runner:latest /bin/bash

# Check Python dependencies
docker run --rm chatdb-test-runner:latest pip list
```

### Tests Skip or Fail
```bash
# Check service availability
kubectl get pods,services

# Test DNS resolution
kubectl run debug --rm -i --tty --image=nicolaka/netshoot -- nslookup training-orchestrator

# Check logs
kubectl logs deployment/training-orchestrator
kubectl logs deployment/kafka
```

### Performance Issues
```bash
# Monitor resource usage
kubectl top pods

# Check network policies
kubectl get networkpolicies

# Analyze slow tests
pytest --durations=10 -v
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build test container
      run: docker build -t chatdb-test-runner:latest kubernetes/test-runner/
    - name: Start test environment
      run: docker-compose -f test-docker-compose.yml up -d
    - name: Run integration tests
      run: docker run --network chatdb_test chatdb-test-runner:latest
```

### Quality Gates
- **Minimum Pass Rate**: 90% of tests must pass
- **Maximum Duration**: 5 minutes for full suite
- **Coverage Requirements**: All critical paths tested
- **Zero Tolerance**: Security and data integrity tests must pass

## Extending the Test Suite

### Adding New Tests
1. Create test file in `tests/` directory
2. Use appropriate pytest markers
3. Follow naming convention: `test_*.py`
4. Add to container via Dockerfile `COPY` instruction

### Test Categories to Add
- **Load Testing**: Stress test with concurrent requests
- **Security Testing**: Authentication, authorization, input validation
- **Data Migration**: Schema changes and data consistency
- **Monitoring**: Metrics collection and alerting validation
- **Backup/Recovery**: Data backup and restoration processes

This comprehensive testing solution ensures the ChatDB microservices architecture operates reliably in production Kubernetes environments.