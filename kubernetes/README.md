# ChatDB Kubernetes Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying ChatDB microservices on Kubernetes using Minikube, along with testing strategies for the overall system flow and robustness.

## Architecture in Kubernetes

```
┌─────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Ingress Controller                  │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────┼─────────────────────────────────┐  │
│  │                Services Layer                         │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│  │
│  │  │Training │  │ Query   │  │   ML    │  │  Model  ││  │
│  │  │  Orch   │  │ Parser  │  │ Engine  │  │Registry ││  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘│  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────┼─────────────────────────────────┐  │
│  │             Message Layer (Kafka)                     │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────┼─────────────────────────────────┐  │
│  │           Data Layer (PostgreSQL)                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Minikube v1.32+ installed
- kubectl v1.28+ installed
- Docker installed
- Helm 3.x installed (optional but recommended)
- 8GB+ RAM available for Minikube
- 20GB+ disk space

## Quick Start

### 1. Start Minikube
```bash
# Start Minikube with adequate resources
minikube start --cpus=4 --memory=8192 --disk-size=20g \
  --kubernetes-version=v1.28.0 \
  --driver=docker

# Enable necessary addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard
```

### 2. Deploy with Make
```bash
# Deploy all services
make deploy-all

# Check deployment status
make status

# Run integration tests
make test-integration
```

## Deployment Strategy

### Namespace Organization
```yaml
chatdb-system/     # Core infrastructure (Kafka, PostgreSQL)
chatdb-services/   # Application microservices
chatdb-monitoring/ # Prometheus, Grafana, Jaeger
chatdb-testing/    # Test runners and tools
```

### Service Dependencies
1. **PostgreSQL** → Base data layer
2. **Kafka** → Message broker (depends on Zookeeper if not using KRaft)
3. **Training Orchestrator** → Depends on PostgreSQL and Kafka
4. **Model Registry** → Depends on PostgreSQL and S3/MinIO
5. **Query Parser** → Depends on Kafka
6. **ML Engine** → Depends on Kafka and Model Registry

## Testing Strategy

### 1. Integration Testing Framework

#### Test Scenarios
```yaml
test-scenarios:
  - name: "End-to-End Query Processing"
    flow:
      1. Submit natural language query
      2. Parse query to SQL
      3. Execute against database
      4. Return formatted results
    
  - name: "ML Training Pipeline"
    flow:
      1. Submit training job
      2. Queue job in Kafka
      3. Process training
      4. Store model in registry
      5. Validate model metadata
    
  - name: "Concurrent Job Processing"
    flow:
      1. Submit multiple training jobs
      2. Verify resource allocation
      3. Check job queuing
      4. Validate completion order
```

#### Running Integration Tests
```bash
# Deploy test environment
kubectl apply -f kubernetes/testing/

# Run all integration tests
kubectl exec -it test-runner -- pytest tests/integration/

# Run specific test suite
kubectl exec -it test-runner -- pytest tests/integration/test_query_flow.py

# Run with coverage
kubectl exec -it test-runner -- pytest --cov=chatdb tests/integration/
```

### 2. Load Testing

#### Using Locust
```python
# locust/locustfile.py
from locust import HttpUser, task, between

class ChatDBUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def submit_query(self):
        self.client.post("/parse", json={
            "query": "Show me all customers"
        })
    
    @task(1)
    def submit_training_job(self):
        self.client.post("/jobs", json={
            "model_name": "test_model",
            "dataset_location": "s3://test/data.csv"
        })
```

Run load tests:
```bash
# Deploy Locust
kubectl apply -f kubernetes/testing/locust.yaml

# Port-forward to access UI
kubectl port-forward svc/locust-master 8089:8089

# Access at http://localhost:8089
```

### 3. Chaos Engineering

#### Fault Injection Tests
```yaml
# chaos/pod-failure.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-failure
spec:
  action: pod-failure
  mode: random-one
  duration: "30s"
  selector:
    namespaces:
      - chatdb-services
    labelSelectors:
      app: training-orchestrator
```

#### Network Chaos
```yaml
# chaos/network-delay.yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: all
  selector:
    namespaces:
      - chatdb-services
  delay:
    latency: "100ms"
    jitter: "10ms"
  duration: "5m"
```

Run chaos tests:
```bash
# Install Chaos Mesh
kubectl create ns chaos-testing
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-testing

# Apply chaos scenarios
kubectl apply -f chaos/

# Monitor system behavior
kubectl logs -f deployment/training-orchestrator
```

### 4. Robustness Testing

#### Test Matrix
| Test Type | Purpose | Tools |
|-----------|---------|-------|
| Circuit Breaking | Prevent cascade failures | Istio/Envoy |
| Retry Logic | Handle transient failures | Custom + Istio |
| Timeout Handling | Prevent hanging requests | Service configs |
| Resource Limits | Prevent resource exhaustion | K8s limits |
| Autoscaling | Handle load spikes | HPA/VPA |
| Backup/Recovery | Data persistence | Velero |

#### Robustness Test Suite
```bash
# Run robustness tests
./scripts/test-robustness.sh

# Test results will be in:
# - reports/robustness-test-results.html
# - metrics/robustness-metrics.json
```

## Monitoring & Observability

### Metrics Stack
```bash
# Deploy Prometheus & Grafana
kubectl apply -f kubernetes/monitoring/

# Access Grafana
kubectl port-forward svc/grafana 3000:3000
# Default: admin/admin

# Access Prometheus
kubectl port-forward svc/prometheus 9090:9090
```

### Distributed Tracing
```bash
# Deploy Jaeger
kubectl apply -f kubernetes/tracing/jaeger.yaml

# Access Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686
```

### Logging
```bash
# Deploy EFK Stack
kubectl apply -f kubernetes/logging/

# Access Kibana
kubectl port-forward svc/kibana 5601:5601
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Deploy to Minikube
on:
  push:
    branches: [main]

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Minikube
        uses: medyagh/setup-minikube@master
        
      - name: Build Images
        run: |
          eval $(minikube docker-env)
          make build-all
          
      - name: Deploy Services
        run: |
          kubectl apply -k kubernetes/base/
          kubectl wait --for=condition=ready pod -l app=chatdb --timeout=300s
          
      - name: Run Integration Tests
        run: |
          make test-integration
          
      - name: Run Load Tests
        run: |
          make test-load
```

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting
```bash
# Check pod status
kubectl get pods -n chatdb-services

# View pod logs
kubectl logs -f pod/<pod-name>

# Describe pod for events
kubectl describe pod/<pod-name>
```

#### 2. Service Communication Issues
```bash
# Test service connectivity
kubectl exec -it <pod> -- curl http://service-name:port/health

# Check service endpoints
kubectl get endpoints

# View service mesh configuration
istioctl analyze
```

#### 3. Kafka Connection Issues
```bash
# Check Kafka pods
kubectl get pods -l app=kafka

# Test Kafka connectivity
kubectl exec -it kafka-0 -- kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# View Kafka logs
kubectl logs -f kafka-0
```

### Debug Commands
```bash
# Enter pod shell
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for local debugging
kubectl port-forward pod/<pod-name> 8080:8080

# View resource usage
kubectl top pods
kubectl top nodes

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

## Performance Tuning

### Resource Optimization
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: training-orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: training-orchestrator
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Next Steps

1. **Security Hardening**
   - Network policies
   - RBAC configuration
   - Secret management with Sealed Secrets
   - Pod security policies

2. **Production Readiness**
   - Multi-region deployment
   - Disaster recovery
   - Backup strategies
   - Blue-green deployments

3. **Advanced Testing**
   - Contract testing
   - Mutation testing
   - Security scanning
   - Compliance validation