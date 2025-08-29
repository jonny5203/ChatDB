# Kubernetes Testing Documentation

This directory contains comprehensive Kubernetes testing documentation for the ChatDB microservices platform.

## Documentation Index

### Core Testing Guides
- [**Kubernetes Manifests Overview**](./kubernetes-manifests.md) - Complete guide to all service manifests
- [**Service Architecture**](./service-architecture.md) - Kubernetes service architecture and dependencies
- [**Testing Strategy**](./testing-strategy.md) - Comprehensive testing approach for Kubernetes deployments
- [**Resource Management**](./resource-management.md) - Resource allocation and scaling configurations

### Operational Guides
- [**Deployment Workflows**](./deployment-workflows.md) - Step-by-step deployment procedures
- [**Health Check Configuration**](./health-checks.md) - Service health monitoring and probes
- [**Troubleshooting Guide**](./troubleshooting.md) - Common issues and resolution procedures
- [**Performance Optimization**](./performance-optimization.md) - Resource optimization and scaling strategies

### Reference Documentation
- [**Service Ports Reference**](./service-ports.md) - Complete port mapping for all services
- [**Environment Variables**](./environment-variables.md) - Configuration reference for all services
- [**Network Policies**](./network-policies.md) - Security and network configuration
- [**Monitoring & Metrics**](./monitoring-metrics.md) - Observability and metrics collection

## Quick Reference

### Service Overview
| Service | Namespace | Port | Health Endpoint | HPA |
|---------|-----------|------|-----------------|-----|
| training-orchestrator | chatdb-services | 8000 | `/health` | 2-10 |
| ml-engine | chatdb-services | 5000 | `/health` | 2-8 |
| model-registry | chatdb-services | 8080 | `/health` | 2-6 |
| query-parser | chatdb-services | 5001 | `/health` | 2-6 |
| db-connector | chatdb-services | 8081 | `/actuator/health` | 2-8 |
| api-gateway | chatdb-services | 80 | `/health` | 2-10 |
| prediction-service | chatdb-services | 8080 | `/health` | 3-15 |
| test-service | chatdb-services | 8001 | `/` | 1-3 |

### Infrastructure Services
| Service | Namespace | Port | Purpose |
|---------|-----------|------|---------|
| postgres | chatdb-system | 5432 | Primary database |
| kafka | chatdb-system | 9092 | Message broker |
| minio | chatdb-system | 9000 | S3-compatible storage |

## Getting Started

1. **Start Here**: [Minikube Deployment Guide](../minikube-deployment-guide.md)
2. **Understand Architecture**: [Service Architecture](./service-architecture.md)
3. **Deploy Services**: [Deployment Workflows](./deployment-workflows.md)
4. **Run Tests**: [Testing Strategy](./testing-strategy.md)
5. **Monitor & Debug**: [Troubleshooting Guide](./troubleshooting.md)

## Prerequisites

- Kubernetes cluster (Minikube recommended for development)
- kubectl configured and connected
- Docker for building images
- 8GB+ RAM, 4+ CPU cores, 20GB+ disk space

## Support

For issues and questions:
- Check the [Troubleshooting Guide](./troubleshooting.md)
- Review [Common Issues](../minikube-troubleshooting-guide.md)
- Validate against [Quick Test Reference](../quick-test-reference.md)