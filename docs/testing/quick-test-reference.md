# Quick Test Reference - ChatDB Test Container

## 🚀 Quick Start Commands

### Build & Run Locally
```bash
cd kubernetes/test-runner
docker build -t chatdb-test-runner:latest .
docker run --rm chatdb-test-runner:latest pytest -v
```

### Test Specific Components
```bash
# Service health checks
docker run --rm chatdb-test-runner:latest pytest tests/test_kubernetes_integration.py::test_service_health_endpoints -v

# Training orchestrator
docker run --rm chatdb-test-runner:latest pytest tests/test_training_orchestrator_k8s.py -v

# Kafka messaging
docker run --rm chatdb-test-runner:latest pytest tests/test_kafka_integration.py -v
```

### Deploy to Kubernetes
```bash
# Create test job
kubectl create job chatdb-tests --image=chatdb-test-runner:latest -- pytest -v ./tests/

# Monitor results
kubectl logs job/chatdb-tests -f

# Clean up
kubectl delete job chatdb-tests
```

## 📋 What Gets Tested

| Component | Tests | What It Validates |
|-----------|-------|-------------------|
| **Services** | 6 health endpoints | DNS resolution, HTTP responses, startup times |
| **Database** | PostgreSQL connection | Data persistence, CRUD operations |
| **Kafka** | Message queue | Producer/consumer, topic management |
| **Networking** | Inter-service calls | Service mesh, network policies |
| **Resources** | Kubernetes limits | CPU/memory allocation, pod status |

## ⏱️ Expected Results

- **Total Duration**: 45-90 seconds
- **Typical Pass Rate**: 95%+ in healthy cluster
- **Services Tested**: 6 microservices + infrastructure
- **Test Categories**: 15+ integration tests

## 🔧 Common Issues & Fixes

| Issue | Symptom | Solution |
|-------|---------|----------|
| Services not ready | Connection refused | `kubectl get pods` - wait for Running status |
| DNS resolution | Name not found | Check service names in `kubectl get svc` |
| Database errors | 500 responses | Verify PostgreSQL pod and connection string |
| Kafka timeout | Connection timeout | Ensure Kafka cluster is deployed |

## 📊 Test Coverage

- ✅ **Service Discovery**: Kubernetes DNS, service mesh
- ✅ **API Endpoints**: REST API functionality, error handling  
- ✅ **Data Layer**: Database persistence, transactions
- ✅ **Messaging**: Kafka producers, consumers, topics
- ✅ **Resilience**: Timeout handling, error recovery
- ✅ **Security**: Non-root execution, input validation

## 🎯 Success Criteria

All tests should **PASS** in a healthy ChatDB deployment:
```
==================== 15 passed, 0 failed, 0 skipped ====================
```

Any failures indicate deployment or configuration issues that need investigation.