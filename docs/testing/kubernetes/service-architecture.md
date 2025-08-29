# ChatDB Kubernetes Service Architecture

Comprehensive overview of the ChatDB microservices architecture deployed on Kubernetes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                             │
│                    (chatdb-services:80)                        │
│                     Load Balancer                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Training    │ │ ML Engine   │ │ Query       │
│ Orchestrator│ │ Service     │ │ Parser      │
│ :8000       │ │ :5000       │ │ :5001       │
└─────┬───────┘ └─────┬───────┘ └─────┬───────┘
      │               │               │
      │         ┌─────┼─────┐         │
      │         │           │         │
      ▼         ▼           ▼         ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Model       │   │ Prediction  │   │ Kafka       │
│ Registry    │   │ Service     │   │ Broker      │
│ :8080       │   │ :8080       │   │ :9092       │
└─────┬───────┘   └─────────────┘   └─────────────┘
      │
      ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ PostgreSQL  │   │ MinIO       │   │ DB          │
│ Database    │   │ S3 Storage  │   │ Connector   │
│ :5432       │   │ :9000       │   │ :8081       │
└─────────────┘   └─────────────┘   └─────────────┘
```

## Service Layers

### 1. Gateway Layer
**API Gateway** - Single entry point for all client requests
- **Purpose**: Request routing, load balancing, authentication, rate limiting
- **Technology**: Go
- **Dependencies**: All application services
- **Scaling**: 2-10 replicas based on request volume

### 2. Application Services Layer
Core business logic services handling specific domains:

#### Training Orchestrator
- **Purpose**: ML model training job management and orchestration
- **Technology**: Python/FastAPI
- **Dependencies**: PostgreSQL, Kafka
- **Key Features**: Job queuing, status tracking, concurrent execution control
- **Scaling**: 2-10 replicas based on job volume

#### ML Engine
- **Purpose**: Model training execution and preprocessing
- **Technology**: Python/FastAPI
- **Dependencies**: Kafka, Model Registry
- **Key Features**: Training pipeline execution, model artifact generation
- **Scaling**: 2-8 replicas based on training load

#### Query Parser
- **Purpose**: Natural language query processing and interpretation
- **Technology**: Python/FastAPI
- **Dependencies**: Kafka, ML Engine
- **Key Features**: NLP processing, query optimization
- **Scaling**: 2-6 replicas based on query volume

#### Model Registry
- **Purpose**: Centralized model versioning and metadata management
- **Technology**: Python/FastAPI
- **Dependencies**: PostgreSQL, MinIO
- **Key Features**: Model versioning, metadata storage, artifact management
- **Scaling**: 2-6 replicas based on model operations

#### Prediction Service
- **Purpose**: Real-time model inference and prediction serving
- **Technology**: Go
- **Dependencies**: Model Registry
- **Key Features**: Model caching, prediction APIs, performance metrics
- **Scaling**: 3-15 replicas based on prediction load (highest scaling)

#### DB Connector
- **Purpose**: Multi-database connectivity and abstraction
- **Technology**: Java/Spring Boot
- **Dependencies**: External databases (PostgreSQL, MySQL, MongoDB)
- **Key Features**: Connection pooling, schema introspection, query execution
- **Scaling**: 2-8 replicas based on database operations

### 3. Infrastructure Layer
Foundational services supporting the application layer:

#### PostgreSQL
- **Purpose**: Primary relational database for application data
- **Data**: Training jobs, model metadata, application state
- **Configuration**: Single instance with persistent storage
- **Resources**: 512Mi memory, 10Gi storage

#### Apache Kafka
- **Purpose**: Event streaming and message broker
- **Usage**: Asynchronous communication between services
- **Configuration**: Single-node setup for development
- **Resources**: 1Gi memory, 5Gi storage

#### MinIO
- **Purpose**: S3-compatible object storage for model artifacts
- **Usage**: Model file storage and retrieval
- **Configuration**: Single instance with persistent storage  
- **Resources**: 512Mi memory, 10Gi storage

## Service Dependencies

### Dependency Graph
```
API Gateway
    ├── Training Orchestrator
    │   ├── PostgreSQL
    │   └── Kafka
    ├── ML Engine
    │   ├── Kafka
    │   └── Model Registry
    │       ├── PostgreSQL
    │       └── MinIO
    ├── Query Parser
    │   ├── Kafka
    │   └── ML Engine (via Kafka)
    ├── Model Registry
    │   ├── PostgreSQL
    │   └── MinIO
    ├── Prediction Service
    │   └── Model Registry
    └── DB Connector
        └── External Databases
```

### Startup Order
1. **Infrastructure Services** (parallel)
   - PostgreSQL
   - Kafka
   - MinIO

2. **Foundation Services** (parallel after infrastructure ready)
   - Training Orchestrator
   - Model Registry

3. **Processing Services** (parallel after foundation ready)
   - ML Engine
   - Query Parser
   - DB Connector
   - Prediction Service

4. **Gateway Services** (after all services ready)
   - API Gateway

## Communication Patterns

### Synchronous Communication (HTTP/REST)
- **API Gateway** → All application services
- **ML Engine** → Model Registry (model retrieval)
- **Prediction Service** → Model Registry (model loading)
- **Training Orchestrator** → PostgreSQL (job management)
- **Model Registry** → PostgreSQL (metadata), MinIO (artifacts)

### Asynchronous Communication (Kafka)
- **Training Orchestrator** → Kafka (job events)
- **ML Engine** ← Kafka (training job consumption)
- **Query Parser** → Kafka (query events)
- **ML Engine** ← Kafka (query processing)

### Service Discovery
All services use Kubernetes DNS for service discovery:
```
{service-name}.{namespace}.svc.cluster.local:{port}
```

Examples:
- `training-orchestrator.chatdb-services.svc.cluster.local:8000`
- `postgres.chatdb-system.svc.cluster.local:5432`

## Network Configuration

### Namespaces
- **`chatdb-system`**: Infrastructure services (postgres, kafka, minio)
- **`chatdb-services`**: Application services (all microservices)
- **`chatdb-testing`**: Test runners and utilities

### Service Types
- **ClusterIP**: All application services (internal only)
- **LoadBalancer**: API Gateway (external access in production)
- **NodePort**: For development/testing access

### Port Allocation
| Service | Internal Port | Service Port | External Access |
|---------|---------------|--------------|-----------------|
| API Gateway | 8080 | 80 | Yes (via LoadBalancer) |
| Training Orchestrator | 8000 | 8000 | No |
| ML Engine | 5000 | 5000 | No |
| Model Registry | 8080 | 8080 | No |
| Query Parser | 5001 | 5001 | No |
| DB Connector | 8081 | 8081 | No |
| Prediction Service | 8080 | 8080 | No |
| Test Service | 8001 | 8001 | No |
| PostgreSQL | 5432 | 5432 | No |
| Kafka | 9092 | 9092 | No |
| MinIO | 9000/9001 | 9000/9001 | No |

## Scaling Strategy

### Horizontal Pod Autoscaler (HPA) Configuration

#### High-Load Services (3-15 replicas)
- **Prediction Service**: CPU 65%, Memory 75%
  - Most resource-intensive due to model inference

#### Medium-Load Services (2-10 replicas)
- **API Gateway**: CPU 70%, Memory 80%
  - Handles all incoming traffic
- **Training Orchestrator**: CPU 70%, Memory 80%
  - Manages compute-intensive training jobs

#### Standard Services (2-8 replicas)
- **ML Engine**: CPU 75%, Memory 85%
- **DB Connector**: CPU 70%, Memory 80%

#### Light Services (2-6 replicas)
- **Model Registry**: CPU 70%, Memory 80%
- **Query Parser**: CPU 70%, Memory 80%

#### Utility Services (1-3 replicas)
- **Test Service**: CPU 60%, Memory 70%

### Resource Allocation Strategy

#### Memory-Intensive Services
- **ML Engine**: 512Mi request, 1Gi limit
- **DB Connector**: 512Mi request, 1Gi limit

#### Standard Services
- **Most Services**: 256Mi request, 512Mi limit

#### Lightweight Services  
- **Test Service**: 128Mi request, 256Mi limit

## Health Monitoring

### Health Check Endpoints
| Service | Health Endpoint | Probe Type |
|---------|-----------------|------------|
| Training Orchestrator | `/health` | HTTP |
| ML Engine | `/health` | HTTP |
| Model Registry | `/health` | HTTP |
| Query Parser | `/health` | HTTP |
| DB Connector | `/actuator/health` | HTTP (Spring Boot) |
| API Gateway | `/health` | HTTP |
| Prediction Service | `/health` | HTTP |
| Test Service | `/` | HTTP |

### Probe Configuration
- **Liveness Probe**: 30s initial delay, 10s period, 5s timeout
- **Readiness Probe**: 10s initial delay, 5s period, 3s timeout
- **Failure Threshold**: 3 consecutive failures

## Security Considerations

### Network Security
- Services communicate only within cluster network
- No direct external access except through API Gateway
- Kafka and databases isolated in system namespace

### Authentication & Authorization
- API Gateway handles external authentication (OIDC configurable)
- Internal service-to-service communication uses service accounts
- Database access through secure connection strings

### Resource Security
- Resource limits prevent resource exhaustion attacks
- Health checks ensure service availability
- Namespace isolation provides security boundaries

## Performance Characteristics

### Latency Targets
- **API Gateway**: <100ms routing overhead
- **Prediction Service**: <200ms inference time
- **DB Connector**: <100ms query execution
- **Other Services**: <500ms request processing

### Throughput Capacity
- **API Gateway**: 1000+ requests/second
- **Prediction Service**: 500+ predictions/second  
- **Training Orchestrator**: 10+ concurrent jobs
- **Kafka**: 1000+ messages/second

### Resource Utilization
- **Target CPU**: 70% average utilization
- **Target Memory**: 80% average utilization
- **Auto-scaling**: Scales up at 80% CPU, down at 30% CPU

This architecture provides a robust, scalable foundation for the ChatDB natural language database interface, with clear separation of concerns and efficient resource utilization.