# ChatDB Testing Framework

## Overview

The ChatDB Testing Framework provides comprehensive testing capabilities for all microservices including unit tests, integration tests, load testing, and chaos engineering. This framework is designed for Kubernetes environments with automated test execution, result aggregation, and monitoring.

## Quick Start

### Prerequisites

- Kubernetes cluster (Minikube, EKS, GKE, etc.)
- kubectl configured for your cluster
- Make utility installed
- Docker (for local development)

### Basic Setup

1. **Start the cluster and deploy services**:
```bash
make setup-minikube          # For local Minikube
make deploy-all              # Deploy all ChatDB services
```

2. **Run comprehensive test suite**:
```bash
make test-all                # Run all test types
```

3. **View test results**:
```bash
kubectl port-forward -n chatdb-testing svc/test-results-web 8080:8080
# Access results at http://localhost:8080
```

## Testing Framework Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Runner   │────│ Results Collector│────│  Results Web    │
│  (Kubernetes)   │    │  (Aggregation)   │    │   (Nginx)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Unit Tests     │    │ Integration Tests│    │  Load Tests     │
│  (pytest/go)    │    │ (Service Mesh)   │    │  (Locust)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────────────────┐
                    │     Chaos Tests         │
                    │   (Chaos Mesh)          │
                    └─────────────────────────┘
```

## Test Types

### 1. Unit Tests

**Purpose**: Test individual service components in isolation

**Technologies**: pytest (Python), go test (Go), JUnit (Java)

**Commands**:
```bash
make test-unit                   # Run all unit tests
cd training-orchestrator && pytest tests/
cd api-gateway && go test ./...
cd db-connector && ./mvnw test
```

**Expected Results**:
- JUnit XML reports in `test-results/`
- Coverage reports (HTML and XML)
- Test execution logs

### 2. Integration Tests

**Purpose**: Test service-to-service interactions and API contracts

**Technologies**: Container-aware pytest, Kubernetes service discovery

**Commands**:
```bash
make test-integration            # Run integration tests
./scripts/test-container.sh integration --verbose
```

**Features**:
- Kubernetes DNS resolution testing
- Database connectivity validation
- Job lifecycle testing
- Concurrent processing validation
- Error recovery testing

### 3. Load & Performance Tests

**Purpose**: Validate system performance under various load conditions

**Technologies**: Locust with Kubernetes deployment

**Commands**:
```bash
make test-load                   # Complete load testing suite
make test-load-quick             # Quick tests (shorter duration)
make test-load-interactive       # Interactive Locust UI
```

**Test Scenarios**:
- **Baseline**: 100-300 users, normal load patterns
- **Spike**: 50→1000 users, burst traffic simulation  
- **Stress**: 200→2000 users, breaking point identification
- **Soak**: 100-200 users, long-term stability

### 4. Chaos Engineering Tests

**Purpose**: Validate system resilience under failure conditions

**Technologies**: Chaos Mesh with comprehensive experiment types

**Commands**:
```bash
make test-chaos                  # Complete chaos testing suite
make test-chaos-pods             # Pod failure experiments only
make test-chaos-network          # Network chaos experiments
make test-chaos-stress           # Resource stress tests
```

**Experiment Types**:
- Pod failures and restarts
- Network partitions and delays
- Resource exhaustion (CPU, memory, I/O)
- Service dependency failures

## Advanced Usage

### Custom Test Execution

#### Unit Testing
```bash
# Run specific test file
cd training-orchestrator
pytest tests/test_main.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run with specific markers
pytest tests/ -m integration
```

#### Integration Testing
```bash
# Run specific integration test
./scripts/test-container.sh integration --test-file test_training_orchestrator_k8s.py

# Run with custom environment
KUBERNETES_SERVICE_HOST=custom-host ./scripts/execute-tests.sh
```

#### Load Testing
```bash
# Custom load test with specific parameters
./scripts/run-performance-tests.sh --experiment baseline --duration 300s

# Interactive load testing
kubectl port-forward -n chatdb-testing svc/locust-master 8089:8089
# Configure tests at http://localhost:8089
```

#### Chaos Engineering
```bash
# Run specific chaos experiment
./scripts/chaos-testing-suite.sh --experiment pod-failures --duration 120s

# Install Chaos Mesh only
./scripts/chaos-testing-suite.sh --install-only

# Access Chaos Mesh dashboard
make chaos-dashboard  # http://localhost:2333
```

### Test Result Management

#### Collecting Results
```bash
# Manual result collection
kubectl exec -n chatdb-testing deployment/test-results-collector -- \
    /scripts/collect-results.sh

# View aggregated results
kubectl port-forward -n chatdb-testing svc/test-results-web 8080:8080
# Access at http://localhost:8080
```

#### Result Structure
```
test-results/
├── latest/                      # Symlink to most recent results
├── test-session-20250830-123456/
│   ├── unit/
│   │   ├── *.xml               # JUnit XML reports
│   │   └── coverage.xml        # Coverage reports
│   ├── integration/
│   │   ├── test-runner.log     # Integration test logs
│   │   └── service-pods.txt    # Service status snapshots
│   ├── load/
│   │   ├── baseline/           # Load test scenario results
│   │   ├── spike/
│   │   └── stress/
│   ├── chaos/
│   │   ├── pod-failures/       # Chaos experiment results
│   │   ├── network-chaos/
│   │   └── resource-stress/
│   ├── reports/
│   │   ├── test-summary.json   # Aggregated metrics
│   │   └── aggregated-metrics.json
│   └── index.html              # Comprehensive results dashboard
```

### Monitoring and Observability

#### Grafana Dashboard
```bash
# Setup monitoring infrastructure
make setup-performance-monitoring

# Access Grafana dashboard
kubectl port-forward -n chatdb-testing svc/grafana 3000:3000
# Login: admin/admin
# Dashboard: "ChatDB Testing Dashboard"
```

#### Prometheus Metrics
The testing framework exposes the following metrics:

- `test_executions_total`: Total test executions by type and suite
- `test_passes_total`: Total successful tests
- `test_failures_total`: Total failed tests  
- `test_duration_seconds`: Test execution duration
- `test_coverage_percentage`: Code coverage percentage
- `service_recovery_time_seconds`: Service recovery times
- `chaos_experiments_total`: Total chaos experiments
- `chaos_experiments_successful`: Successful chaos experiments

#### Accessing Metrics
```bash
# View raw Prometheus metrics
kubectl port-forward -n chatdb-testing svc/test-metrics-exporter 8000:8000
curl http://localhost:8000/metrics

# Access Prometheus UI
kubectl port-forward -n chatdb-testing svc/prometheus 9090:9090
# Query metrics at http://localhost:9090
```

## Configuration

### Environment Variables

#### Test Execution
```bash
# Container detection
KUBERNETES_SERVICE_HOST         # Auto-detected in cluster
DOCKER_ENV                     # Set to 'true' for container execution

# Test configuration
MAX_CONCURRENT_JOBS=2          # Training orchestrator job limits
TEST_TIMEOUT=300               # Test timeout in seconds
PYTEST_ARGS="--verbose"       # Additional pytest arguments

# Performance testing
LOCUST_USERS=100               # Number of concurrent users
LOCUST_SPAWN_RATE=10           # Users spawned per second
TEST_DURATION=300s             # Test duration
```

#### Service Configuration
```bash
# Database
DATABASE_URL=postgresql://user:password@postgres/training_db
POSTGRES_HOST=postgres.chatdb-system.svc.cluster.local
POSTGRES_PORT=5432

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=training_jobs

# AWS S3 (for Model Registry)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your_bucket
```

### Test Configuration Files

#### pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers = 
    unit: Unit tests
    integration: Integration tests
    kubernetes: Kubernetes-specific tests
    slow: Slow running tests
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --junit-xml=test-results/junit.xml
    --html=test-results/pytest_report.html
    --self-contained-html
    --cov=.
    --cov-report=html:test-results/coverage_html
    --cov-report=xml:test-results/coverage.xml
    --cov-fail-under=80
```

#### Locust Configuration
```python
# locustfile.py configuration
class ChatDBUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://training-orchestrator.chatdb-services.svc.cluster.local:8000"
    
    @task(5)
    def create_job(self):
        # Test job creation
        pass
    
    @task(3)
    def check_health(self):
        # Health check testing
        pass
```

## Extending the Test Suite

### Adding New Unit Tests

1. **Create test file** in the appropriate service's `tests/` directory:
```python
# tests/test_new_feature.py
import pytest
from your_service import new_feature

def test_new_feature_success():
    result = new_feature.process_data(valid_input)
    assert result.status == "success"

def test_new_feature_validation():
    with pytest.raises(ValueError):
        new_feature.process_data(invalid_input)

@pytest.mark.integration
def test_new_feature_database():
    # Integration test with database
    pass
```

2. **Run the new tests**:
```bash
cd your-service
pytest tests/test_new_feature.py -v
```

### Adding Integration Tests

1. **Create test in `kubernetes/test-runner/tests/`**:
```python
# test_new_integration.py
import pytest
import requests
import os

@pytest.mark.kubernetes
def test_new_service_integration():
    base_url = get_service_url("new-service")
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200

def get_service_url(service_name):
    if os.environ.get('KUBERNETES_SERVICE_HOST'):
        return f"http://{service_name}.chatdb-services.svc.cluster.local:8000"
    else:
        return f"http://localhost:8000"
```

2. **Update test runner configuration** if needed.

### Adding Load Test Scenarios

1. **Extend Locust test file**:
```python
# In kubernetes/testing/locust.yaml ConfigMap
@task(2)
def test_new_endpoint(self):
    response = self.client.post("/new-endpoint", json={
        "parameter": "test_value"
    })
    if response.status_code == 200:
        self.success_count += 1
```

2. **Add new test scenario**:
```bash
# In run-performance-tests.sh
run_load_test_scenario "new-scenario" 500 20 "5m" "Testing new endpoint performance"
```

### Adding Chaos Experiments

1. **Create new chaos manifest**:
```yaml
# kubernetes/chaos/new-chaos-experiment.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: new-service-chaos
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: one
  duration: "60s"
  selector:
    namespaces: [chatdb-services]
    labelSelectors:
      app: new-service
```

2. **Update chaos test suite** to include the new experiment.

## Troubleshooting

### Common Issues

#### 1. Tests Not Finding Services
**Problem**: Tests fail with "connection refused" or "service not found"

**Solution**:
```bash
# Check service status
kubectl get pods -n chatdb-services
kubectl get services -n chatdb-services

# Verify service health
kubectl exec -n chatdb-services deployment/training-orchestrator -- \
    curl http://localhost:8000/health

# Check DNS resolution
kubectl exec -n chatdb-testing deployment/test-runner -- \
    nslookup training-orchestrator.chatdb-services.svc.cluster.local
```

#### 2. Test Results Not Appearing
**Problem**: Test results are not collected or visible

**Solution**:
```bash
# Check results collector status
kubectl get pods -n chatdb-testing -l app=test-results-collector
kubectl logs -n chatdb-testing deployment/test-results-collector

# Verify persistent volume
kubectl get pv,pvc -n chatdb-testing

# Manual collection
kubectl exec -n chatdb-testing deployment/test-results-collector -- \
    /scripts/collect-results.sh
```

#### 3. Chaos Mesh Experiments Not Starting
**Problem**: Chaos experiments don't execute

**Solution**:
```bash
# Check Chaos Mesh status
kubectl get pods -n chaos-testing
kubectl logs -n chaos-testing deployment/chaos-controller-manager

# Verify RBAC permissions
kubectl auth can-i delete pods --as=system:serviceaccount:chaos-testing:chaos-controller-manager -n chatdb-services

# Check experiment status
kubectl describe podchaos training-orchestrator-pod-kill -n chaos-testing
```

#### 4. Performance Tests Timeout
**Problem**: Load tests fail due to timeouts

**Solution**:
```bash
# Check Locust status
kubectl get pods -n chatdb-testing -l app=locust-master
kubectl logs -n chatdb-testing deployment/locust-master

# Verify target service capacity
kubectl top pods -n chatdb-services
kubectl describe pods -n chatdb-services

# Adjust test parameters
./scripts/run-performance-tests.sh --duration 120s  # Shorter duration
```

#### 5. Grafana Dashboard Not Loading
**Problem**: Grafana dashboard shows no data

**Solution**:
```bash
# Check metrics exporter
kubectl get pods -n chatdb-testing -l app=test-metrics-exporter
kubectl logs -n chatdb-testing deployment/test-metrics-exporter

# Verify Prometheus scraping
kubectl port-forward -n chatdb-testing svc/test-metrics-exporter 8000:8000
curl http://localhost:8000/metrics

# Check Grafana data source configuration
# Login to Grafana and verify Prometheus data source connectivity
```

### Debug Commands

```bash
# General cluster health
kubectl get pods --all-namespaces
kubectl top nodes

# Service-specific debugging
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --tail=100

# Network connectivity testing
kubectl run debug --image=curlimages/curl --rm -i --restart=Never -- \
    curl http://service-name.namespace.svc.cluster.local:port/health

# Resource usage monitoring
kubectl top pods -n chatdb-services --sort-by=cpu
kubectl top pods -n chatdb-services --sort-by=memory
```

### Performance Tuning

#### Resource Limits
Adjust resource limits based on your cluster capacity:

```yaml
# In deployment manifests
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"  # Increase for memory-intensive tests
    cpu: "500m"      # Increase for CPU-intensive tests
```

#### Test Timeouts
Configure appropriate timeouts for your environment:

```bash
# Environment variables
export TEST_TIMEOUT=600          # 10 minutes for slower clusters
export PYTEST_ARGS="--timeout=300"  # 5 minute per-test timeout
export LOCUST_DURATION="300s"   # 5 minute load tests
```

#### Concurrent Execution
Adjust concurrency based on cluster resources:

```bash
export MAX_CONCURRENT_JOBS=1     # Reduce for smaller clusters
export LOCUST_WORKERS=2         # Reduce Locust workers
export CHAOS_EXPERIMENT_DURATION="60s"  # Shorter chaos experiments
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: ChatDB Testing Suite
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  comprehensive-testing:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Kubernetes
      uses: helm/kind-action@v1.2.0
      with:
        cluster_name: chatdb-test
        config: .github/kind-config.yaml
    
    - name: Deploy ChatDB Services
      run: |
        make deploy-all
        kubectl wait --for=condition=ready pod --all -n chatdb-services --timeout=300s
    
    - name: Run Unit Tests
      run: make test-unit
    
    - name: Run Integration Tests
      run: make test-integration
    
    - name: Run Load Tests (Quick)
      run: make test-load-quick
    
    - name: Run Chaos Tests (Quick)
      run: ./scripts/chaos-testing-suite.sh --duration 60s
    
    - name: Collect Results
      run: |
        kubectl exec -n chatdb-testing deployment/test-results-collector -- \
            /scripts/collect-results.sh
    
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: test-results/
    
    - name: Generate Test Report
      run: |
        kubectl port-forward -n chatdb-testing svc/test-results-web 8080:8080 &
        sleep 10
        curl -o test-report.html http://localhost:8080/latest/index.html
    
    - name: Upload HTML Report
      uses: actions/upload-artifact@v3
      with:
        name: test-report
        path: test-report.html
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    environment {
        KUBECONFIG = credentials('kubeconfig')
        CLUSTER_NAME = 'chatdb-test'
    }
    
    stages {
        stage('Setup') {
            steps {
                script {
                    sh 'make deploy-all'
                    sh 'kubectl wait --for=condition=ready pod --all -n chatdb-services --timeout=300s'
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh 'make test-unit'
            }
            post {
                always {
                    publishTestResults testResultsPattern: '**/test-results/*.xml'
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                sh 'make test-integration'
            }
        }
        
        stage('Performance Tests') {
            steps {
                sh 'make test-load-quick'
            }
        }
        
        stage('Chaos Engineering') {
            steps {
                sh './scripts/chaos-testing-suite.sh --duration 120s'
            }
        }
        
        stage('Collect Results') {
            steps {
                sh '''
                    kubectl exec -n chatdb-testing deployment/test-results-collector -- \
                        /scripts/collect-results.sh
                '''
            }
        }
    }
    
    post {
        always {
            script {
                // Archive test results
                archiveArtifacts artifacts: 'test-results/**/*', fingerprint: true
                
                // Publish HTML reports
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'test-results/latest',
                    reportFiles: 'index.html',
                    reportName: 'ChatDB Test Report'
                ])
            }
        }
    }
}
```

## Best Practices

### Test Development
1. **Write tests first** (TDD approach)
2. **Keep tests isolated** and independent
3. **Use meaningful test names** that describe the scenario
4. **Mock external dependencies** in unit tests
5. **Test both success and failure cases**

### Test Execution
1. **Run tests frequently** during development
2. **Use appropriate test markers** to categorize tests
3. **Monitor test execution time** and optimize slow tests
4. **Review test results** and fix flaky tests
5. **Keep test data clean** and isolated

### Test Maintenance
1. **Update tests** when code changes
2. **Remove obsolete tests** when features are removed
3. **Refactor test code** to reduce duplication
4. **Document test scenarios** and expected outcomes
5. **Monitor test coverage** and aim for >80%

### Performance Testing
1. **Start with baseline tests** before optimization
2. **Test realistic scenarios** based on expected usage
3. **Monitor resource usage** during tests
4. **Set appropriate SLA targets** for response times
5. **Test gradually increasing load** to find limits

### Chaos Engineering
1. **Start with low-impact experiments** in non-production
2. **Have clear hypotheses** about system behavior
3. **Monitor system recovery** and measure MTTR
4. **Document learnings** from each experiment
5. **Gradually increase experiment scope** as confidence grows

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review test results and fix flaky tests
2. **Monthly**: Update test scenarios based on new features
3. **Quarterly**: Review and optimize test execution times
4. **Annually**: Assess test coverage and gaps

### Updating the Framework

1. **Update dependencies** regularly for security patches
2. **Monitor Chaos Mesh releases** for new experiment types
3. **Update Grafana dashboards** with new metrics
4. **Review and update documentation** as the system evolves

### Getting Help

1. **Check the troubleshooting section** first
2. **Review test logs** for specific error messages
3. **Check Kubernetes events** for cluster-level issues
4. **Consult service documentation** for API changes
5. **Create GitHub issues** for bugs or feature requests

## Conclusion

The ChatDB Testing Framework provides comprehensive testing capabilities covering all aspects of the system from unit tests to chaos engineering. By following this guide, you can effectively validate your system's functionality, performance, and resilience.

For additional support or to contribute improvements, please refer to the main project repository and documentation.