# Minikube Deployment Guide for ChatDB Testing

## Overview

This guide provides step-by-step instructions for deploying ChatDB services to Minikube and running the comprehensive test suite to validate the entire system integration.

## Prerequisites

### System Requirements
- **RAM**: 8GB+ available for Minikube
- **CPU**: 4+ cores recommended
- **Disk**: 20GB+ free space
- **OS**: Linux, macOS, or Windows with WSL2

### Software Dependencies
```bash
# Install Minikube (latest version)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Install kubectl
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Install Docker (if not already installed)
sudo apt-get update && sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
```

## Step 1: Initialize Minikube Cluster

### Start Minikube with Optimal Configuration
```bash
# Start Minikube with adequate resources for ChatDB
minikube start \
  --cpus=4 \
  --memory=8192 \
  --disk-size=20g \
  --kubernetes-version=v1.28.0 \
  --driver=docker

# Verify cluster is running
minikube status
```

### Enable Essential Addons
```bash
# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard
minikube addons enable registry

# Verify addons are enabled
minikube addons list | grep enabled
```

### Configure Docker Environment
```bash
# Set docker environment to use Minikube's Docker daemon
eval $(minikube docker-env)

# Verify Docker is pointing to Minikube
docker ps | grep k8s
```

## Step 2: Build Images in Minikube

### Build All Service Images
```bash
# Navigate to project root
cd /path/to/ChatDB

# Build all service images
make build-all

# Or build individually
docker build -t training-orchestrator:latest training-orchestrator/
docker build -t ml-engine:latest ml_engine/
docker build -t model-registry:latest model-registry/
docker build -t query-parser:latest query-parser/
docker build -t db-connector:latest db-connector/
docker build -t api-gateway:latest api-gateway/
docker build -t prediction-service:latest prediction-service/
docker build -t test-service:latest test-service/

# Build the test container
docker build -t chatdb-test-runner:latest kubernetes/test-runner/
```

### Verify Images
```bash
# List built images
docker images | grep -E "(training-orchestrator|ml-engine|model-registry|query-parser|db-connector|api-gateway|prediction-service|test-service|chatdb-test-runner)"
```

## Step 3: Deploy Infrastructure Services

### Deploy PostgreSQL
```bash
# Create namespace for infrastructure
kubectl create namespace chatdb-system

# Deploy PostgreSQL
kubectl apply -f kubernetes/infrastructure/postgres.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
```

### Deploy Kafka
```bash
# Deploy Kafka
kubectl apply -f kubernetes/infrastructure/kafka.yaml
kubectl wait --for=condition=ready pod -l app=kafka -n chatdb-system --timeout=300s

# Verify Kafka is running
kubectl exec -n chatdb-system kafka-0 -- kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

### Deploy MinIO (for Model Registry)
```bash
# Deploy MinIO for S3-compatible storage
kubectl apply -f kubernetes/infrastructure/minio.yaml
kubectl wait --for=condition=ready pod -l app=minio -n chatdb-system --timeout=300s
```

## Step 4: Deploy ChatDB Microservices

### Create Application Namespace
```bash
kubectl create namespace chatdb-services
```

### Deploy Services in Dependency Order
```bash
# 1. Deploy Training Orchestrator (depends on PostgreSQL + Kafka)
kubectl apply -f kubernetes/services/training-orchestrator.yaml
kubectl wait --for=condition=ready pod -l app=training-orchestrator -n chatdb-services --timeout=300s

# 2. Deploy Model Registry (depends on PostgreSQL + MinIO)
kubectl apply -f kubernetes/services/model-registry.yaml
kubectl wait --for=condition=ready pod -l app=model-registry -n chatdb-services --timeout=300s

# 3. Deploy ML Engine (depends on Kafka + Model Registry)
kubectl apply -f kubernetes/services/ml-engine.yaml
kubectl wait --for=condition=ready pod -l app=ml-engine -n chatdb-services --timeout=300s

# 4. Deploy Query Parser (depends on Kafka)
kubectl apply -f kubernetes/services/query-parser.yaml
kubectl wait --for=condition=ready pod -l app=query-parser -n chatdb-services --timeout=300s

# 5. Deploy DB Connector (depends on external databases)
kubectl apply -f kubernetes/services/db-connector.yaml
kubectl wait --for=condition=ready pod -l app=db-connector -n chatdb-services --timeout=300s

# 6. Deploy Prediction Service (depends on Model Registry)
kubectl apply -f kubernetes/services/prediction-service.yaml
kubectl wait --for=condition=ready pod -l app=prediction-service -n chatdb-services --timeout=300s

# 7. Deploy API Gateway (depends on all services)
kubectl apply -f kubernetes/services/api-gateway.yaml
kubectl wait --for=condition=ready pod -l app=api-gateway -n chatdb-services --timeout=300s

# 8. Deploy Test Service
kubectl apply -f kubernetes/services/test-service.yaml
kubectl wait --for=condition=ready pod -l app=test-service -n chatdb-services --timeout=300s
```

### Verify All Services Are Running
```bash
# Check pod status
kubectl get pods -n chatdb-services -o wide

# Check service endpoints
kubectl get services -n chatdb-services

# Test service health endpoints
kubectl run debug --rm -i --tty --image=nicolaka/netshoot -- bash
# Inside the debug pod:
# curl http://training-orchestrator.chatdb-services:8000/health
# curl http://ml-engine.chatdb-services:5000/health
# curl http://model-registry.chatdb-services:8080/health
# curl http://query-parser.chatdb-services:5001/health
# curl http://db-connector.chatdb-services:8081/actuator/health
# curl http://api-gateway.chatdb-services:80/health
# curl http://prediction-service.chatdb-services:8080/health
# curl http://test-service.chatdb-services:8001/
```

## Step 5: Run Comprehensive Tests

### Deploy Test Runner Job
```bash
# Create test namespace
kubectl create namespace chatdb-testing

# Deploy test runner job
cat <<EOF | kubectl apply -f -
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
        imagePullPolicy: Never
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
        - name: API_GATEWAY_URL
          value: "http://api-gateway.chatdb-services:80"
        - name: PREDICTION_SERVICE_URL
          value: "http://prediction-service.chatdb-services:8080"
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
EOF
```

### Monitor Test Execution
```bash
# Watch job status
kubectl get jobs -n chatdb-testing -w

# Follow test logs in real-time
kubectl logs -n chatdb-testing job/chatdb-integration-tests -f

# Check final results
kubectl logs -n chatdb-testing job/chatdb-integration-tests --tail=50
```

### Expected Test Results
```
==================== TEST SESSION STARTS ====================
platform linux -- Python 3.11.x, pytest-8.x.x
collected 19 items

tests/test_kubernetes_integration.py::test_service_health_endpoints[training-orchestrator] PASSED [ 5%]
tests/test_kubernetes_integration.py::test_service_health_endpoints[ml-engine] PASSED [10%]
tests/test_kubernetes_integration.py::test_service_health_endpoints[model-registry] PASSED [15%]
tests/test_kubernetes_integration.py::test_service_health_endpoints[query-parser] PASSED [21%]
tests/test_kubernetes_integration.py::test_service_health_endpoints[db-connector] PASSED [26%]
tests/test_kubernetes_integration.py::test_service_health_endpoints[test-service] PASSED [31%]
tests/test_kubernetes_integration.py::test_service_discovery_dns PASSED [36%]
tests/test_kubernetes_integration.py::test_inter_service_communication PASSED [42%]
tests/test_kubernetes_integration.py::test_persistent_storage PASSED [47%]

tests/test_training_orchestrator_k8s.py::test_training_orchestrator_health PASSED [52%]
tests/test_training_orchestrator_k8s.py::test_create_training_job_k8s PASSED [57%]
tests/test_training_orchestrator_k8s.py::test_list_training_jobs_k8s PASSED [63%]

tests/test_kafka_integration.py::test_kafka_connectivity PASSED [68%]
tests/test_kafka_integration.py::test_training_job_message_production PASSED [73%]
tests/test_kafka_integration.py::test_message_consumption PASSED [78%]

==================== 19 passed, 0 failed ====================
Duration: 2m 34s
```

## Step 6: Interactive Testing & Debugging

### Access Services Directly
```bash
# Port-forward to access services locally
kubectl port-forward -n chatdb-services svc/training-orchestrator 8000:8000 &
kubectl port-forward -n chatdb-services svc/ml-engine 5000:5000 &
kubectl port-forward -n chatdb-services svc/model-registry 8080:8080 &
kubectl port-forward -n chatdb-services svc/query-parser 5001:5001 &
kubectl port-forward -n chatdb-services svc/db-connector 8081:8081 &
kubectl port-forward -n chatdb-services svc/api-gateway 8082:80 &
kubectl port-forward -n chatdb-services svc/prediction-service 8083:8080 &
kubectl port-forward -n chatdb-services svc/test-service 8001:8001 &

# Test endpoints locally
curl http://localhost:8000/health
curl http://localhost:5000/health
curl http://localhost:8080/health
curl http://localhost:5001/health
curl http://localhost:8081/actuator/health
curl http://localhost:8082/health
curl http://localhost:8083/health
curl http://localhost:8001/
```

### Run Specific Test Categories
```bash
# Test only service connectivity
kubectl exec -n chatdb-testing -it job/chatdb-integration-tests -- \
  pytest tests/test_kubernetes_integration.py::test_service_health_endpoints -v

# Test only Kafka integration
kubectl exec -n chatdb-testing -it job/chatdb-integration-tests -- \
  pytest tests/test_kafka_integration.py -v

# Test with specific markers
kubectl exec -n chatdb-testing -it job/chatdb-integration-tests -- \
  pytest -m "integration and not slow" -v
```

### Debug Failed Tests
```bash
# Get detailed test output
kubectl exec -n chatdb-testing -it job/chatdb-integration-tests -- \
  pytest --tb=long --verbose ./tests/

# Interactive debugging session
kubectl exec -n chatdb-testing -it job/chatdb-integration-tests -- /bin/bash
# Inside container:
# python -c "import requests; print(requests.get('http://training-orchestrator.chatdb-services:8000/health').json())"
```

## Step 7: Load Testing (Optional)

### Deploy Locust for Load Testing
```bash
# Deploy Locust
cat <<EOF | kubectl apply -f -
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
        volumeMounts:
        - name: locust-config
          mountPath: /locust
      volumes:
      - name: locust-config
        configMap:
          name: locust-config
---
apiVersion: v1
kind: Service
metadata:
  name: locust-master
  namespace: chatdb-testing
spec:
  selector:
    app: locust-master
  ports:
  - port: 8089
    targetPort: 8089
EOF

# Access Locust UI
kubectl port-forward -n chatdb-testing svc/locust-master 8089:8089
# Open http://localhost:8089
```

## Cleanup

### Stop Test Jobs
```bash
kubectl delete job chatdb-integration-tests -n chatdb-testing
kubectl delete namespace chatdb-testing
```

### Remove Services
```bash
kubectl delete namespace chatdb-services
kubectl delete namespace chatdb-system
```

### Stop Minikube
```bash
minikube stop
minikube delete  # Complete cleanup
```

## Troubleshooting

⚠️ **For comprehensive troubleshooting, see the [Minikube Troubleshooting Guide](./minikube-troubleshooting-guide.md)**

### Quick Troubleshooting

#### Critical Issue: API Server Connection Failures
If you see errors like "dial tcp [::1]:8443: connect: connection refused":

```bash
# Check cluster status
minikube status

# If API server is stopped, recreate cluster
minikube delete
minikube start --memory=4096 --cpus=2 --disk-size=20gb

# Verify cluster health
kubectl get nodes
kubectl get storageclass
```

#### Resource Configuration Issues
```bash
# Delete and recreate with proper resources if you see allocation warnings
minikube delete
minikube start --cpus=4 --memory=8192 --disk-size=20g
```

### Common Issues (Quick Fixes)

#### 1. Images Not Found
```bash
# Ensure docker environment is set
eval $(minikube docker-env)
make build-all
```

#### 2. Services Not Connecting
```bash
# Check service DNS and restart CoreDNS if needed
kubectl rollout restart deployment/coredns -n kube-system
```

#### 3. Storage Issues
```bash
# Verify storage provisioner is running
kubectl get pods -n kube-system | grep storage-provisioner
kubectl get storageclass
```

#### 4. Complete Cluster Reset (Nuclear Option)
```bash
# If all else fails
minikube delete
minikube start --memory=8192 --cpus=4 --disk-size=20g
make deploy-all
```

### Health Check Script
```bash
#!/bin/bash
echo "=== Quick Health Check ==="
minikube status
kubectl get nodes
kubectl get pods -n kube-system | grep -E "(coredns|storage-provisioner)"
kubectl get storageclass
echo "=== Health Check Complete ==="
```

### Monitoring Commands
```bash
# Monitor cluster resources
watch kubectl get pods -A

# View recent events
kubectl get events --sort-by='.lastTimestamp' -A | tail -10

# Check service logs
kubectl logs -f deployment/training-orchestrator -n chatdb-services
```

📖 **For detailed troubleshooting procedures, systematic diagnostics, and prevention strategies, refer to the [Minikube Troubleshooting Guide](./minikube-troubleshooting-guide.md)**

This guide provides complete end-to-end deployment and testing of ChatDB on Minikube, ensuring all services are properly validated in a Kubernetes environment.