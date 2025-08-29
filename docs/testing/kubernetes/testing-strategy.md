# Kubernetes Testing Strategy

Comprehensive testing approach for ChatDB Kubernetes deployments covering all testing levels from unit to end-to-end.

## Testing Pyramid

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← Kubernetes Integration
                    │   (Slow/Few)    │     Full system validation
                    └─────────────────┘
                  ┌───────────────────────┐
                  │  Integration Tests    │  ← Service-to-Service
                  │  (Medium/Moderate)    │     API contracts
                  └───────────────────────┘
                ┌─────────────────────────────┐
                │      Unit Tests             │  ← Individual Services
                │     (Fast/Many)             │     Business logic
                └─────────────────────────────┘
```

## Test Categories

### 1. Unit Tests (Service-Level)
**Scope**: Individual service business logic
**Environment**: Local development
**Speed**: < 1 second per test
**Coverage Target**: 80%+

#### Test Structure per Service
```bash
# Python services (training-orchestrator, ml-engine, etc.)
tests/
├── conftest.py          # Shared fixtures
├── test_main.py         # API endpoint tests
├── test_models.py       # Data model tests
├── test_database.py     # Database layer tests
└── test_business_logic.py

# Java services (db-connector)
src/test/java/
├── {package}/
│   ├── ApplicationTests.java
│   ├── controller/
│   │   └── ControllerTests.java
│   └── service/
│       └── ServiceTests.java

# Go services (api-gateway, prediction-service)
*_test.go files alongside implementation
```

#### Running Unit Tests
```bash
# Python services
cd training-orchestrator && pipenv run pytest tests/
cd ml-engine && pipenv run pytest tests/
cd model-registry && pytest tests/
cd query-parser && pipenv run pytest tests/

# Java services  
cd db-connector && ./mvnw test

# Go services
cd api-gateway && go test ./...
cd prediction-service && go test ./...
```

### 2. Integration Tests (Service-to-Service)
**Scope**: API contracts and service interactions
**Environment**: Kubernetes cluster
**Speed**: 5-30 seconds per test
**Coverage**: All service endpoints

#### Test Runner Container
**Location**: `kubernetes/test-runner/`
**Image**: `chatdb-test-runner:latest`
**Base**: Python 3.11 with testing dependencies

#### Test Structure
```
kubernetes/test-runner/tests/
├── test_kubernetes_integration.py    # Service health and discovery
├── test_training_orchestrator_k8s.py # Training workflow tests
├── test_kafka_integration.py         # Message broker tests
├── test_api_contracts.py             # API contract validation
├── test_database_integration.py      # Database connectivity
└── test_end_to_end_workflow.py      # Complete user workflows
```

#### Key Integration Tests

**Service Health Checks**
```python
@pytest.mark.parametrize("service,url,expected_status", [
    ("training-orchestrator", f"{TRAINING_ORCHESTRATOR_URL}/health", 200),
    ("ml-engine", f"{ML_ENGINE_URL}/health", 200),
    ("model-registry", f"{MODEL_REGISTRY_URL}/health", 200),
    ("query-parser", f"{QUERY_PARSER_URL}/health", 200),
    ("db-connector", f"{DB_CONNECTOR_URL}/actuator/health", 200),
    ("api-gateway", f"{API_GATEWAY_URL}/health", 200),
    ("prediction-service", f"{PREDICTION_SERVICE_URL}/health", 200),
    ("test-service", f"{TEST_SERVICE_URL}/", 200),
])
def test_service_health_endpoints(service, url, expected_status):
    response = requests.get(url, timeout=10)
    assert response.status_code == expected_status
```

**Service Discovery & DNS**
```python
def test_service_discovery_dns():
    """Test Kubernetes DNS resolution for all services"""
    services = [
        "training-orchestrator.chatdb-services.svc.cluster.local",
        "ml-engine.chatdb-services.svc.cluster.local",
        "postgres.chatdb-system.svc.cluster.local",
        "kafka.chatdb-system.svc.cluster.local",
    ]
    
    for service in services:
        result = subprocess.run(['nslookup', service], 
                              capture_output=True, text=True)
        assert result.returncode == 0, f"DNS resolution failed for {service}"
```

**Database Connectivity**
```python
def test_database_connectivity():
    """Test PostgreSQL connection from application services"""
    import psycopg2
    
    conn = psycopg2.connect(
        host="postgres.chatdb-system.svc.cluster.local",
        port=5432,
        database="training_db",
        user="user",
        password="password"
    )
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    conn.close()
```

**Kafka Integration**
```python
def test_kafka_message_production_consumption():
    """Test Kafka message flow between services"""
    from kafka import KafkaProducer, KafkaConsumer
    
    bootstrap_servers = "kafka.chatdb-system.svc.cluster.local:9092"
    topic = "test-messages"
    
    # Producer test
    producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
    future = producer.send(topic, b"test message")
    result = future.get(timeout=10)
    
    # Consumer test
    consumer = KafkaConsumer(topic, bootstrap_servers=[bootstrap_servers],
                           auto_offset_reset='earliest', consumer_timeout_ms=5000)
    
    messages = []
    for message in consumer:
        messages.append(message.value)
        break
    
    assert len(messages) > 0
    assert b"test message" in messages
```

#### Running Integration Tests
```bash
# Deploy test runner as Kubernetes Job
kubectl apply -f kubernetes/testing/integration-tests.yaml

# Monitor test execution
kubectl logs -n chatdb-testing job/chatdb-integration-tests -f

# Get test results
kubectl logs -n chatdb-testing job/chatdb-integration-tests --tail=100
```

### 3. End-to-End Tests (Full System)
**Scope**: Complete user workflows
**Environment**: Full Kubernetes deployment
**Speed**: 1-5 minutes per test
**Coverage**: Critical user paths

#### E2E Test Scenarios

**Complete Training Workflow**
```python
def test_complete_training_workflow():
    """Test full model training pipeline"""
    
    # 1. Submit training job
    job_data = {
        "name": "test-training-job",
        "model_type": "linear_regression",
        "dataset_path": "/data/sample.csv",
        "hyperparameters": {"learning_rate": 0.01}
    }
    
    response = requests.post(f"{API_GATEWAY_URL}/api/training/jobs", json=job_data)
    assert response.status_code == 201
    job_id = response.json()["job_id"]
    
    # 2. Monitor job status
    max_wait_time = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        response = requests.get(f"{API_GATEWAY_URL}/api/training/jobs/{job_id}")
        assert response.status_code == 200
        
        status = response.json()["status"]
        if status == "completed":
            break
        elif status == "failed":
            pytest.fail(f"Training job failed: {response.json()}")
        
        time.sleep(10)
    else:
        pytest.fail("Training job did not complete within timeout")
    
    # 3. Verify model registration
    response = requests.get(f"{API_GATEWAY_URL}/api/models")
    assert response.status_code == 200
    models = response.json()["models"]
    assert any(model["training_job_id"] == job_id for model in models)
```

**Query Processing Pipeline**
```python
def test_query_processing_pipeline():
    """Test natural language query processing"""
    
    # 1. Submit natural language query
    query_data = {
        "query": "Show me all users created in the last month",
        "database_connection": "default"
    }
    
    response = requests.post(f"{API_GATEWAY_URL}/api/queries", json=query_data)
    assert response.status_code == 200
    
    query_id = response.json()["query_id"]
    
    # 2. Get processed SQL
    response = requests.get(f"{API_GATEWAY_URL}/api/queries/{query_id}/sql")
    assert response.status_code == 200
    assert "SELECT" in response.json()["sql"].upper()
    
    # 3. Execute query (if test database available)
    response = requests.post(f"{API_GATEWAY_URL}/api/queries/{query_id}/execute")
    # Status could be 200 (success) or 400 (no test data) - both acceptable
    assert response.status_code in [200, 400]
```

### 4. Load Testing
**Scope**: Performance and scalability validation
**Environment**: Production-like Kubernetes cluster
**Tools**: Locust, custom load generators

#### Load Test Configuration
```yaml
# kubernetes/testing/locust.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-master
  namespace: chatdb-testing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: locust-master
  template:
    metadata:
      labels:
        app: locust-master
    spec:
      containers:
      - name: locust
        image: locustio/locust:2.17.0
        command: ["locust", "-f", "/locust/locustfile.py", "--master"]
        ports:
        - containerPort: 8089
        env:
        - name: TARGET_HOST
          value: "http://api-gateway.chatdb-services:80"
        volumeMounts:
        - name: locust-config
          mountPath: /locust
      volumes:
      - name: locust-config
        configMap:
          name: locust-config
```

#### Load Test Scenarios
```python
# locustfile.py
from locust import HttpUser, task, between

class ChatDBUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def check_health_endpoints(self):
        """Test health endpoint load"""
        services = ["/health", "/api/training/jobs", "/api/models"]
        for endpoint in services:
            self.client.get(endpoint)
    
    @task(1)
    def submit_training_job(self):
        """Test training job submission load"""
        job_data = {
            "name": f"load-test-job-{self.generate_id()}",
            "model_type": "linear_regression",
            "dataset_path": "/data/sample.csv"
        }
        self.client.post("/api/training/jobs", json=job_data)
    
    def generate_id(self):
        import uuid
        return str(uuid.uuid4())[:8]
```

### 5. Chaos Testing
**Scope**: Resilience and fault tolerance
**Environment**: Staging/Production Kubernetes cluster
**Tools**: Chaos Mesh, custom failure injection

#### Chaos Test Scenarios
```yaml
# Pod failure test
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: training-orchestrator-pod-kill
  namespace: chatdb-testing
spec:
  action: pod-kill
  mode: one
  duration: "30s"
  selector:
    namespaces:
      - chatdb-services
    labelSelectors:
      app: training-orchestrator
```

## Test Automation Pipeline

### GitHub Actions Workflow
```yaml
name: Kubernetes Testing Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Python service tests
      - name: Test Training Orchestrator
        run: |
          cd training-orchestrator
          pipenv install --dev
          pipenv run pytest tests/ --cov=.
      
      # Java service tests  
      - name: Test DB Connector
        run: |
          cd db-connector
          ./mvnw test
      
      # Go service tests
      - name: Test API Gateway
        run: |
          cd api-gateway
          go test ./... -v

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Minikube
        uses: medyagh/setup-minikube@master
        with:
          minikube-version: 1.32.0
          kubernetes-version: 1.28.0
          driver: docker
          
      - name: Deploy Infrastructure
        run: |
          kubectl apply -f kubernetes/infrastructure/
          kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
          
      - name: Build and Deploy Services
        run: |
          eval $(minikube docker-env)
          make build-all
          kubectl apply -f kubernetes/services/
          
      - name: Run Integration Tests
        run: |
          kubectl apply -f kubernetes/testing/integration-tests.yaml
          kubectl wait --for=condition=complete job/chatdb-integration-tests -n chatdb-testing --timeout=600s
          kubectl logs job/chatdb-integration-tests -n chatdb-testing
```

## Test Environment Management

### Environment Setup
```bash
#!/bin/bash
# scripts/setup-test-environment.sh

set -e

echo "Setting up test environment..."

# Start Minikube
minikube start --memory=8192 --cpus=4 --disk-size=20g

# Enable addons
minikube addons enable ingress metrics-server

# Build images
eval $(minikube docker-env)
make build-all

# Deploy infrastructure
kubectl apply -f kubernetes/infrastructure/
echo "Waiting for infrastructure to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n chatdb-system --timeout=300s

# Deploy services
kubectl apply -f kubernetes/services/
echo "Waiting for services to be ready..."
kubectl wait --for=condition=ready pod -l app=training-orchestrator -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=ml-engine -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=model-registry -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=query-parser -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=db-connector -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=api-gateway -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=prediction-service -n chatdb-services --timeout=300s

echo "Test environment ready!"
echo "Access API Gateway: minikube service api-gateway -n chatdb-services --url"
```

### Test Data Management
```bash
# scripts/setup-test-data.sh
#!/bin/bash

echo "Setting up test data..."

# Port forward to access services
kubectl port-forward -n chatdb-system svc/postgres 5432:5432 &
PG_PID=$!

# Wait for port forward
sleep 5

# Create test data
psql -h localhost -p 5432 -U user -d training_db -c "
  INSERT INTO training_jobs (name, status, model_type) 
  VALUES ('test-job-1', 'completed', 'linear_regression');
"

# Create test model files
kubectl exec -n chatdb-system deployment/minio -- mc mb local/chatdb-models
kubectl cp test-data/sample-model.pkl minio:/tmp/
kubectl exec -n chatdb-system deployment/minio -- mc cp /tmp/sample-model.pkl local/chatdb-models/

# Cleanup
kill $PG_PID

echo "Test data setup complete!"
```

## Test Metrics and Reporting

### Test Coverage Requirements
- **Unit Tests**: 80% code coverage minimum
- **Integration Tests**: 100% API endpoint coverage
- **E2E Tests**: 100% critical user path coverage

### Performance Benchmarks
- **API Response Time**: < 500ms (95th percentile)
- **Training Job Completion**: < 10 minutes for test jobs
- **Query Processing**: < 2 seconds for simple queries
- **System Recovery**: < 30 seconds after pod restart

### Test Result Reporting
```bash
# Generate test report
pytest --cov=. --cov-report=html --cov-report=xml tests/
go test -coverprofile=coverage.out ./...
mvn jacoco:report

# Upload to CI/CD dashboard
curl -s https://codecov.io/bash | bash
```

## Continuous Testing Strategy

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Run unit tests
        entry: make test-unit
        language: system
        pass_filenames: false
```

### Nightly Integration Tests
```bash
# cron job: 0 2 * * *
#!/bin/bash
# Run full integration test suite nightly

make setup-test-environment
make test-integration
make test-load
make cleanup-test-environment
```

This comprehensive testing strategy ensures robust validation of the ChatDB Kubernetes deployment across all levels, from individual service functionality to complete system integration and performance under load.