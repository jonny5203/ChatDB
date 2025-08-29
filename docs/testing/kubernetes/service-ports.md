# Service Ports Reference

Complete port mapping and networking reference for all ChatDB services.

## Application Services (`chatdb-services` namespace)

### Training Orchestrator
- **Container Port**: 8000
- **Service Port**: 8000
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **External Access**: Via API Gateway only

### ML Engine
- **Container Port**: 5000
- **Service Port**: 5000
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **External Access**: Via API Gateway only

### Model Registry
- **Container Port**: 8080
- **Service Port**: 8080
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **External Access**: Via API Gateway only

### Query Parser
- **Container Port**: 5001
- **Service Port**: 5001
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **External Access**: Via API Gateway only

### DB Connector
- **Container Port**: 8081
- **Service Port**: 8081
- **Protocol**: HTTP
- **Health Check**: `GET /actuator/health` (Spring Boot Actuator)
- **External Access**: Via API Gateway only

### API Gateway
- **Container Port**: 8080
- **Service Port**: 80
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **External Access**: Direct (LoadBalancer/NodePort)

### Prediction Service
- **Container Port**: 8080 (HTTP), 9090 (Metrics)
- **Service Port**: 8080 (HTTP), 9090 (Metrics)
- **Protocol**: HTTP
- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` on port 9090
- **External Access**: Via API Gateway only

### Test Service
- **Container Port**: 8001
- **Service Port**: 8001
- **Protocol**: HTTP
- **Health Check**: `GET /`
- **External Access**: Testing only

## Infrastructure Services (`chatdb-system` namespace)

### PostgreSQL
- **Container Port**: 5432
- **Service Port**: 5432
- **Protocol**: PostgreSQL
- **Health Check**: TCP socket check
- **External Access**: Internal only

### Apache Kafka
- **Container Port**: 9092 (Kafka), 2181 (Zookeeper)
- **Service Port**: 9092 (Kafka), 2181 (Zookeeper)
- **Protocol**: Kafka/TCP
- **Health Check**: TCP socket check
- **External Access**: Internal only

### MinIO
- **Container Port**: 9000 (API), 9001 (Console)
- **Service Port**: 9000 (API), 9001 (Console)
- **Protocol**: HTTP/S3 API
- **Health Check**: `GET /minio/health/ready`
- **External Access**: Internal only

## Service Discovery DNS Names

### Application Services
```bash
# Full cluster DNS names
training-orchestrator.chatdb-services.svc.cluster.local:8000
ml-engine.chatdb-services.svc.cluster.local:5000
model-registry.chatdb-services.svc.cluster.local:8080
query-parser.chatdb-services.svc.cluster.local:5001
db-connector.chatdb-services.svc.cluster.local:8081
api-gateway.chatdb-services.svc.cluster.local:80
prediction-service.chatdb-services.svc.cluster.local:8080
test-service.chatdb-services.svc.cluster.local:8001

# Short names (within same namespace)
training-orchestrator:8000
ml-engine:5000
model-registry:8080
query-parser:5001
db-connector:8081
api-gateway:80
prediction-service:8080
test-service:8001
```

### Infrastructure Services
```bash
# Full cluster DNS names
postgres.chatdb-system.svc.cluster.local:5432
kafka.chatdb-system.svc.cluster.local:9092
minio.chatdb-system.svc.cluster.local:9000

# Cross-namespace access (from chatdb-services)
postgres.chatdb-system:5432
kafka.chatdb-system:9092
minio.chatdb-system:9000
```

## Port Forwarding for Development

### Access Services Locally
```bash
# Application services
kubectl port-forward -n chatdb-services svc/training-orchestrator 8000:8000 &
kubectl port-forward -n chatdb-services svc/ml-engine 5000:5000 &
kubectl port-forward -n chatdb-services svc/model-registry 8080:8080 &
kubectl port-forward -n chatdb-services svc/query-parser 5001:5001 &
kubectl port-forward -n chatdb-services svc/db-connector 8081:8081 &
kubectl port-forward -n chatdb-services svc/api-gateway 8082:80 &
kubectl port-forward -n chatdb-services svc/prediction-service 8083:8080 &
kubectl port-forward -n chatdb-services svc/test-service 8001:8001 &

# Infrastructure services
kubectl port-forward -n chatdb-system svc/postgres 5432:5432 &
kubectl port-forward -n chatdb-system svc/kafka 9092:9092 &
kubectl port-forward -n chatdb-system svc/minio 9000:9000 &
kubectl port-forward -n chatdb-system svc/minio 9001:9001 &
```

### Test Local Access
```bash
# Application services
curl http://localhost:8000/health          # Training Orchestrator
curl http://localhost:5000/health          # ML Engine
curl http://localhost:8080/health          # Model Registry
curl http://localhost:5001/health          # Query Parser
curl http://localhost:8081/actuator/health # DB Connector
curl http://localhost:8082/health          # API Gateway
curl http://localhost:8083/health          # Prediction Service
curl http://localhost:8001/               # Test Service

# Infrastructure services
psql -h localhost -p 5432 -U user -d training_db    # PostgreSQL
kafka-console-consumer --bootstrap-server localhost:9092 --list # Kafka
curl http://localhost:9000/minio/health/ready       # MinIO API
curl http://localhost:9001                          # MinIO Console
```

## Network Policies

### Default Policy (Recommended for Production)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: chatdb-services
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### Allow Internal Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal
  namespace: chatdb-services
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: chatdb-services
  - from:
    - namespaceSelector:
        matchLabels:
          name: chatdb-system
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: chatdb-services
  - to:
    - namespaceSelector:
        matchLabels:
          name: chatdb-system
  - to: {} # Allow external access (DNS, etc.)
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

## Service Mesh Considerations

### Istio Configuration (Optional)
If using Istio service mesh:

```yaml
# Enable automatic sidecar injection
apiVersion: v1
kind: Namespace
metadata:
  name: chatdb-services
  labels:
    istio-injection: enabled

# Virtual Service for API Gateway
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-gateway
  namespace: chatdb-services
spec:
  hosts:
  - api-gateway.chatdb-services.svc.cluster.local
  http:
  - route:
    - destination:
        host: api-gateway.chatdb-services.svc.cluster.local
        port:
          number: 80
```

## Load Balancing

### Service Load Balancing
All services use Kubernetes default round-robin load balancing:
- **Algorithm**: Round-robin across healthy pods
- **Health Checks**: Readiness probes determine pod availability
- **Session Affinity**: None (stateless services)

### API Gateway Load Balancing
- **External**: LoadBalancer service or Ingress controller
- **Internal**: Round-robin to multiple API Gateway pods
- **Failover**: Automatic to healthy pods

## Monitoring Ports

### Prometheus Metrics
- **Prediction Service**: `:9090/metrics`
- **Other Services**: Health endpoints can be scraped for basic metrics

### Health Check Ports
All services expose health checks on their primary HTTP port:
- **Standard**: `{service-port}/health`
- **Spring Boot**: `{service-port}/actuator/health`

## Security Groups / Firewall Rules

### Required Port Access
```bash
# Inbound (for external access)
80/tcp    # API Gateway HTTP
443/tcp   # API Gateway HTTPS (if configured)

# Internal cluster communication (all ports)
# Kubernetes manages internal networking

# Outbound (for external dependencies)
53/tcp,53/udp   # DNS resolution
80/tcp,443/tcp  # External HTTP/HTTPS APIs
```

## Troubleshooting Port Issues

### Check Service Endpoints
```bash
kubectl get endpoints -n chatdb-services
kubectl get endpoints -n chatdb-system
```

### Test Internal Connectivity
```bash
# From debug pod
kubectl run debug --rm -i --tty --image=nicolaka/netshoot -- bash

# Test specific service ports
nc -zv training-orchestrator.chatdb-services 8000
nc -zv postgres.chatdb-system 5432
```

### Check Pod Port Bindings
```bash
kubectl describe pod -l app=training-orchestrator -n chatdb-services
kubectl logs -l app=training-orchestrator -n chatdb-services
```

### Validate Service Configuration
```bash
kubectl describe service training-orchestrator -n chatdb-services
kubectl get service training-orchestrator -n chatdb-services -o yaml
```

## Common Port Conflicts

### Avoiding Conflicts
- **API Gateway**: Uses port 80 (standard HTTP) instead of 8080
- **Model Registry & Prediction Service**: Both use 8080 internally but different services
- **MinIO**: Uses both 9000 (API) and 9001 (Console) - ensure both are exposed

### Port Mapping Strategy
- **Infrastructure**: Standard ports (5432, 9092, 9000)
- **Application**: High ports (5000-8001) to avoid conflicts
- **Gateway**: Standard HTTP ports (80, 443) for external access

This port configuration ensures clean separation, easy troubleshooting, and optimal performance across all ChatDB services.