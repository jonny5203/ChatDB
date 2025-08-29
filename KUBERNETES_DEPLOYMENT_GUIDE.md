# ChatDB Kubernetes Deployment Guide

## Overview

This guide provides complete instructions for deploying all ChatDB microservices to a Minikube cluster for seamless integration and testing.

## Complete Service Architecture

```yaml
Infrastructure (chatdb-system namespace):
  ✅ PostgreSQL - Database persistence (port 5432)
  ✅ Kafka - Message broker (port 9092)
  ✅ MinIO - Object storage S3-compatible (ports 9000/9001)

Services (chatdb-services namespace):
  ✅ training-orchestrator:8000 - ML job management
  ✅ query-parser:8002 - NLP query processing
  ✅ ml-engine:8003 - ML training & inference
  ✅ model-registry:8004 - Model storage & metadata
  ✅ test-service:8001 - Health checks & testing
```

## Created Components

### Service Manifests
- **training-orchestrator.yaml** - Job management with PostgreSQL + Kafka
- **query-parser.yaml** - NLP processing with Kafka integration
- **ml-engine.yaml** - ML processing with higher resource allocation (2Gi memory)
- **model-registry.yaml** - Model storage with PostgreSQL + MinIO (2 replicas)
- **test-service.yaml** - Simple health check service

### Infrastructure
- **postgres.yaml** - PostgreSQL StatefulSet with persistent storage
- **kafka.yaml** - Kafka StatefulSet with topic auto-creation
- **minio.yaml** - MinIO deployment for S3-compatible object storage

### Deployment Scripts
- **setup-minikube.sh** - One-command cluster setup with required addons
- **build-images.sh** - Build all Docker images in Minikube environment
- **deploy-all.sh** - Complete deployment with proper dependency order

## Quick Start Instructions

### 1. Setup Minikube Cluster
```bash
# Start Minikube with optimal resources
./scripts/setup-minikube.sh

# This will:
# - Start Minikube (4 CPU, 8GB RAM, 20GB disk)
# - Enable ingress, metrics-server, dashboard addons
# - Configure Docker environment
```

### 2. Build Docker Images
```bash
# Build all service images for Minikube
./scripts/build-images.sh

# This builds:
# - chatdb/training-orchestrator:latest
# - chatdb/query-parser:latest
# - chatdb/ml-engine:latest
# - chatdb/model-registry:latest
# - chatdb/test-service:latest
```

### 3. Deploy Everything
```bash
# Deploy complete system with dependencies
./scripts/deploy-all.sh

# This will:
# - Create namespaces (chatdb-system, chatdb-services)
# - Deploy infrastructure (PostgreSQL, Kafka, MinIO)
# - Wait for infrastructure readiness
# - Deploy all application services
# - Wait for service readiness
```

### 4. Verify Deployment
```bash
# Check infrastructure status
kubectl get pods -n chatdb-system

# Check service status
kubectl get pods -n chatdb-services

# Check all services are running
kubectl get pods -A | grep chatdb
```

### 5. Test Services
```bash
# Port-forward to test training orchestrator
kubectl port-forward -n chatdb-services svc/training-orchestrator 8000:8000
curl http://localhost:8000/health

# Port-forward to test query parser
kubectl port-forward -n chatdb-services svc/query-parser 8002:8002
curl http://localhost:8002/health

# Port-forward to test service
kubectl port-forward -n chatdb-services svc/test-service 8001:8001
curl http://localhost:8001/
```

## Service Details

### Training Orchestrator (Port 8000)
- **Purpose**: ML job management and orchestration
- **Dependencies**: PostgreSQL, Kafka
- **Resources**: 512Mi memory, 500m CPU
- **Replicas**: 2 (with HPA scaling 2-10)
- **Health Check**: `/health`

### Query Parser (Port 8002)
- **Purpose**: Natural language query processing
- **Dependencies**: Kafka
- **Resources**: 1Gi memory, 500m CPU
- **Environment**: Kafka connection, query topics
- **Health Check**: `/health`

### ML Engine (Port 8003)
- **Purpose**: ML model training and inference
- **Dependencies**: Kafka, Model Registry
- **Resources**: 2Gi memory, 1000m CPU (highest allocation)
- **Environment**: Kafka + Model Registry connections
- **Health Check**: `/health` (45s initial delay for ML loading)

### Model Registry (Port 8004)
- **Purpose**: Model storage and metadata management
- **Dependencies**: PostgreSQL, MinIO
- **Resources**: 512Mi memory, 500m CPU
- **Replicas**: 2 (high availability)
- **Environment**: Database + S3 storage connections
- **Health Check**: `/health`

### Test Service (Port 8001)
- **Purpose**: Health checks and service validation
- **Dependencies**: None
- **Resources**: 256Mi memory, 200m CPU (minimal)
- **Health Check**: `/` (simple endpoint)

## Infrastructure Services

### PostgreSQL
- **StatefulSet** with persistent 10Gi storage
- **Database**: `training_db`
- **Credentials**: user/password (configurable)
- **Health Check**: pg_isready command

### Kafka
- **StatefulSet** with KRaft mode (no Zookeeper)
- **Topics**: queries, training_jobs, predictions (auto-created)
- **Storage**: 10Gi persistent volume
- **Health Check**: Kafka broker API validation

### MinIO
- **S3-compatible object storage**
- **Credentials**: minioadmin/minioadmin
- **Storage**: 20Gi persistent volume
- **Ports**: 9000 (API), 9001 (Console)

## Networking

### Internal Service Communication
```yaml
# Services communicate using Kubernetes DNS:
kafka.chatdb-system.svc.cluster.local:9092
postgres.chatdb-system.svc.cluster.local:5432
minio.chatdb-system.svc.cluster.local:9000
training-orchestrator.chatdb-services.svc.cluster.local:8000
model-registry.chatdb-services.svc.cluster.local:8004
```

### External Access
```bash
# Use kubectl port-forward for external access:
kubectl port-forward -n chatdb-services svc/[service-name] [local-port]:[service-port]

# Access Minikube dashboard:
minikube dashboard

# Access MinIO console:
kubectl port-forward -n chatdb-system svc/minio 9001:9001
# Open http://localhost:9001 (minioadmin/minioadmin)
```

## Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status and events
kubectl get pods -n chatdb-services
kubectl describe pod [pod-name] -n chatdb-services
kubectl logs -f [pod-name] -n chatdb-services
```

#### Service Communication Issues
```bash
# Test internal connectivity
kubectl exec -it [pod-name] -n chatdb-services -- curl http://[service-name]:8000/health

# Check service endpoints
kubectl get endpoints -n chatdb-services
```

#### Resource Issues
```bash
# Check resource usage
kubectl top pods -n chatdb-services
kubectl top nodes

# Check resource limits
kubectl describe pod [pod-name] -n chatdb-services
```

### Useful Commands

```bash
# Restart all services
kubectl rollout restart deployment -n chatdb-services

# Scale a service
kubectl scale deployment [service-name] -n chatdb-services --replicas=3

# View logs from all services
kubectl logs -f -n chatdb-services --all-containers=true --prefix=true

# Delete and redeploy
kubectl delete -f kubernetes/services/
kubectl apply -f kubernetes/services/
```

## Integration Testing

### End-to-End Test Flow
```bash
# 1. Submit training job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"test-model","dataset_location":"s3://test/data.csv"}'

# 2. Check job status
curl http://localhost:8000/jobs/[job-id]

# 3. Test query parsing
curl -X POST http://localhost:8002/parse \
  -H "Content-Type: application/json" \
  -d '{"query":"Show me all customers"}'

# 4. Verify MinIO storage
kubectl port-forward -n chatdb-system svc/minio 9001:9001
# Access http://localhost:9001 to check stored models
```

## Cleanup

```bash
# Delete all services
kubectl delete -f kubernetes/services/

# Delete infrastructure
kubectl delete -f kubernetes/infrastructure/

# Delete namespaces
kubectl delete namespace chatdb-system chatdb-services chatdb-monitoring chatdb-testing

# Stop Minikube
minikube stop
minikube delete
```

## Next Steps

1. **Add Ingress**: Create ingress rules for external HTTP access
2. **Add Monitoring**: Deploy Prometheus + Grafana for metrics
3. **Add Logging**: Deploy EFK stack for centralized logging
4. **Security**: Add network policies and RBAC
5. **CI/CD**: Integrate with GitHub Actions for automated deployment

---

**Your complete ChatDB microservices system is now ready for deployment! 🚀**

All services will communicate seamlessly through Kubernetes internal networking, with proper dependency management and health checks ensuring reliable operation.