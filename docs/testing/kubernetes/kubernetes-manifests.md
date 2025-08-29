# Kubernetes Manifests Overview

Complete guide to all Kubernetes manifests for the ChatDB microservices platform.

## Manifest Structure

All service manifests follow a consistent four-component structure:

1. **ConfigMap** - Environment variables and configuration
2. **Deployment** - Pod specification with resources and health checks  
3. **Service** - Network exposure and service discovery
4. **HorizontalPodAutoscaler** - Auto-scaling configuration

## Application Services (`chatdb-services` namespace)

### Training Orchestrator
**File**: `kubernetes/services/training-orchestrator.yaml`
```yaml
# Key Configuration
DATABASE_URL: postgresql://user:password@postgres.chatdb-system.svc.cluster.local:5432/training_db
KAFKA_BOOTSTRAP_SERVERS: kafka.chatdb-system.svc.cluster.local:9092
MAX_CONCURRENT_JOBS: "2"

# Resources
requests: memory 256Mi, cpu 250m
limits: memory 512Mi, cpu 500m

# Scaling: 2-10 replicas, CPU 70%, Memory 80%
```

### ML Engine
**File**: `kubernetes/services/ml-engine.yaml`
```yaml
# Key Configuration  
KAFKA_BOOTSTRAP_SERVERS: kafka.chatdb-system.svc.cluster.local:9092
MODEL_REGISTRY_URL: http://model-registry.chatdb-services.svc.cluster.local:8080

# Resources
requests: memory 512Mi, cpu 500m
limits: memory 1Gi, cpu 1000m

# Scaling: 2-8 replicas, CPU 75%, Memory 85%
```

### Model Registry
**File**: `kubernetes/services/model-registry.yaml`
```yaml
# Key Configuration
DATABASE_URL: postgresql://user:password@postgres.chatdb-system.svc.cluster.local:5432/model_registry_db
AWS_ACCESS_KEY_ID: minio
AWS_SECRET_ACCESS_KEY: minio123
S3_ENDPOINT_URL: http://minio.chatdb-system.svc.cluster.local:9000
S3_BUCKET_NAME: chatdb-models

# Resources
requests: memory 256Mi, cpu 250m
limits: memory 512Mi, cpu 500m

# Scaling: 2-6 replicas, CPU 70%, Memory 80%
```

### Query Parser
**File**: `kubernetes/services/query-parser.yaml`
```yaml
# Key Configuration
KAFKA_BOOTSTRAP_SERVERS: kafka.chatdb-system.svc.cluster.local:9092
ML_ENGINE_URL: http://ml-engine.chatdb-services.svc.cluster.local:5000

# Resources
requests: memory 256Mi, cpu 250m
limits: memory 512Mi, cpu 500m

# Scaling: 2-6 replicas, CPU 70%, Memory 80%
```

### DB Connector
**File**: `kubernetes/services/db-connector.yaml`
```yaml
# Key Configuration (Java/Spring Boot)
SPRING_PROFILES_ACTIVE: kubernetes
SERVER_PORT: "8081"

# Resources
requests: memory 512Mi, cpu 250m
limits: memory 1Gi, cpu 500m

# Health Check: /actuator/health (Spring Boot Actuator)
# Scaling: 2-8 replicas, CPU 70%, Memory 80%
```

### API Gateway
**File**: `kubernetes/services/api-gateway.yaml`
```yaml
# Key Configuration
TRAINING_ORCHESTRATOR_URL: http://training-orchestrator.chatdb-services.svc.cluster.local:8000
ML_ENGINE_URL: http://ml-engine.chatdb-services.svc.cluster.local:5000
MODEL_REGISTRY_URL: http://model-registry.chatdb-services.svc.cluster.local:8080
QUERY_PARSER_URL: http://query-parser.chatdb-services.svc.cluster.local:5001
DB_CONNECTOR_URL: http://db-connector.chatdb-services.svc.cluster.local:8081
PREDICTION_SERVICE_URL: http://prediction-service.chatdb-services.svc.cluster.local:8080
OIDC_ENABLED: "false"
CORS_ENABLED: "true"
RATE_LIMIT_ENABLED: "true"

# Resources
requests: memory 256Mi, cpu 250m
limits: memory 512Mi, cpu 500m

# Scaling: 2-10 replicas, CPU 70%, Memory 80%
```

### Prediction Service
**File**: `kubernetes/services/prediction-service.yaml`
```yaml
# Key Configuration
MODEL_REGISTRY_URL: http://model-registry.chatdb-services.svc.cluster.local:8080
CACHE_TTL: "3600"
MAX_CACHE_SIZE: "100"
METRICS_PORT: "9090"

# Resources
requests: memory 256Mi, cpu 250m
limits: memory 512Mi, cpu 500m

# Dual Ports: 8080 (HTTP), 9090 (Metrics)
# Scaling: 3-15 replicas, CPU 65%, Memory 75%
```

### Test Service
**File**: `kubernetes/services/test-service.yaml`
```yaml
# Key Configuration
# Basic health check service for testing

# Resources
requests: memory 128Mi, cpu 100m
limits: memory 256Mi, cpu 200m

# Scaling: 1-3 replicas, CPU 60%, Memory 70%
```

## Infrastructure Services (`chatdb-system` namespace)

### PostgreSQL
**File**: `kubernetes/infrastructure/postgres.yaml`
```yaml
# Configuration
POSTGRES_DB: training_db
POSTGRES_USER: user
POSTGRES_PASSWORD: password

# Persistent Volume: 10Gi
# Resources: memory 512Mi, cpu 500m
```

### Apache Kafka
**File**: `kubernetes/infrastructure/kafka.yaml`
```yaml
# Single-node Kafka setup for development
# Zookeeper + Kafka in same pod
# Persistent Volume: 5Gi

# Ports: 9092 (Kafka), 2181 (Zookeeper)
# Resources: memory 1Gi, cpu 500m
```

### MinIO (S3-compatible storage)
**File**: `kubernetes/infrastructure/minio.yaml`
```yaml
# Configuration
MINIO_ROOT_USER: minio
MINIO_ROOT_PASSWORD: minio123

# Persistent Volume: 10Gi
# Ports: 9000 (API), 9001 (Console)
# Resources: memory 512Mi, cpu 500m
```

## Common Patterns

### ConfigMap Structure
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {service}-config
  namespace: chatdb-services
data:
  # Service-specific environment variables
  # Database URLs with full cluster DNS names
  # Feature flags and configuration
```

### Deployment Patterns
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service}
  namespace: chatdb-services
  labels:
    app: {service}
    component: backend|gateway
spec:
  replicas: 2  # Minimum for HA
  selector:
    matchLabels:
      app: {service}
  template:
    metadata:
      labels:
        app: {service}
        version: v1
    spec:
      containers:
      - name: {service}
        image: chatdb/{service}:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: {port}
          name: http
        envFrom:
        - configMapRef:
            name: {service}-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

### Service Patterns
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {service}
  namespace: chatdb-services
  labels:
    app: {service}
spec:
  selector:
    app: {service}
  ports:
  - port: {external-port}
    targetPort: {container-port}
    protocol: TCP
    name: http
  type: ClusterIP
```

### HPA Patterns
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {service}-hpa
  namespace: chatdb-services
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {service}
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Validation Commands

### Apply All Manifests
```bash
# Infrastructure first
kubectl apply -f kubernetes/infrastructure/

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n chatdb-system --timeout=300s

# Application services in dependency order
kubectl apply -f kubernetes/services/training-orchestrator.yaml
kubectl apply -f kubernetes/services/model-registry.yaml
kubectl apply -f kubernetes/services/ml-engine.yaml
kubectl apply -f kubernetes/services/query-parser.yaml
kubectl apply -f kubernetes/services/db-connector.yaml
kubectl apply -f kubernetes/services/prediction-service.yaml
kubectl apply -f kubernetes/services/api-gateway.yaml
kubectl apply -f kubernetes/services/test-service.yaml
```

### Verify Deployments
```bash
# Check all pods are running
kubectl get pods -n chatdb-system
kubectl get pods -n chatdb-services

# Check services are exposed
kubectl get services -n chatdb-system
kubectl get services -n chatdb-services

# Check HPA status
kubectl get hpa -n chatdb-services

# Verify ConfigMaps
kubectl get configmaps -n chatdb-services
```

### Health Check All Services
```bash
# Use debug pod to test internal connectivity
kubectl run debug --rm -i --tty --image=nicolaka/netshoot -- bash

# Inside debug pod, test each service
curl http://training-orchestrator.chatdb-services:8000/health
curl http://ml-engine.chatdb-services:5000/health
curl http://model-registry.chatdb-services:8080/health
curl http://query-parser.chatdb-services:5001/health
curl http://db-connector.chatdb-services:8081/actuator/health
curl http://api-gateway.chatdb-services:80/health
curl http://prediction-service.chatdb-services:8080/health
curl http://test-service.chatdb-services:8001/
```

## Resource Summary

### Total Resource Requirements
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB RAM, 8 CPU cores
- **Storage**: 25GB+ persistent volumes

### Per-Service Resource Allocation
| Service | Memory Request | Memory Limit | CPU Request | CPU Limit |
|---------|---------------|--------------|-------------|-----------|
| training-orchestrator | 256Mi | 512Mi | 250m | 500m |
| ml-engine | 512Mi | 1Gi | 500m | 1000m |
| model-registry | 256Mi | 512Mi | 250m | 500m |
| query-parser | 256Mi | 512Mi | 250m | 500m |
| db-connector | 512Mi | 1Gi | 250m | 500m |
| api-gateway | 256Mi | 512Mi | 250m | 500m |
| prediction-service | 256Mi | 512Mi | 250m | 500m |
| test-service | 128Mi | 256Mi | 100m | 200m |

### Infrastructure Resources
| Service | Memory | CPU | Storage |
|---------|--------|-----|---------|
| postgres | 512Mi | 500m | 10Gi |
| kafka | 1Gi | 500m | 5Gi |
| minio | 512Mi | 500m | 10Gi |

## Best Practices

1. **Always deploy infrastructure services first**
2. **Wait for readiness before deploying dependent services**
3. **Use full cluster DNS names for inter-service communication**
4. **Configure appropriate resource requests and limits**
5. **Enable health checks for all services**
6. **Use HPA for auto-scaling based on load**
7. **Monitor resource usage and adjust as needed**
8. **Test service connectivity after deployment**