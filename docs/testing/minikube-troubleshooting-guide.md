# Minikube Troubleshooting Guide for ChatDB

## Overview

This guide documents common Minikube issues encountered during ChatDB deployment and provides systematic solutions. It covers the specific problems encountered during cluster initialization and their resolutions.

## Critical Issue: API Server Connection Failures

### Problem Description
The most critical issue encountered was API server connectivity problems during Minikube initialization, manifesting as:

```
error: error validating "/etc/kubernetes/addons/storage-provisioner.yaml": 
error validating data: failed to download openapi: 
Get "https://localhost:8443/openapi/v2?timeout=32s": 
dial tcp [::1]:8443: connect: connection refused
```

### Root Cause Analysis
1. **API Server State**: The API server was in "Stopped" state while other components (host, kubelet) were running
2. **Validation Dependency**: Kubernetes addon validation requires active API server connection
3. **Storage Provisioner Impact**: Default storage class and provisioner couldn't be enabled
4. **Cascading Effects**: This prevented proper cluster initialization and resource creation

### Solution Steps

#### 1. Immediate Diagnosis
```bash
# Check cluster component status
minikube status

# Expected problematic output:
# host: Running
# kubelet: Running
# apiserver: Stopped  ← This is the problem
# kubeconfig: Configured
```

#### 2. Cluster Recreation (Recommended Solution)
```bash
# Complete cluster deletion and recreation
minikube delete
minikube start --memory=4096 --cpus=2 --disk-size=20gb

# Verify successful startup
minikube status
kubectl get nodes
kubectl get pods --all-namespaces
```

#### 3. Verification Steps
```bash
# Confirm API server is accessible
kubectl get componentstatuses

# Verify storage classes are working
kubectl get storageclass

# Test resource creation
kubectl apply --dry-run=client -f kubernetes/infrastructure/
```

## Common Minikube Issues and Solutions

### Issue 1: Resource Allocation Warnings

**Problem:**
```
❗ You cannot change the memory size for an existing minikube cluster. 
Please first delete the cluster.
```

**Solution:**
```bash
# Delete and recreate with proper resources
minikube delete
minikube start --cpus=4 --memory=8192 --disk-size=20g
```

**Prevention:**
- Always specify resource requirements on initial cluster creation
- Document resource requirements in deployment scripts
- Use configuration files for consistent settings

### Issue 2: Storage Provisioner Validation Errors

**Problem:**
```
error validating "/etc/kubernetes/addons/storage-provisioner.yaml": 
failed to download openapi
```

**Root Cause:** API server not fully initialized before addon validation

**Solution:**
```bash
# Method 1: Wait for API server
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Method 2: Manual addon management
minikube addons disable storage-provisioner
minikube addons enable storage-provisioner

# Method 3: Complete restart (most reliable)
minikube stop && minikube start
```

### Issue 3: Docker Environment Misconfiguration

**Problem:** Images built locally not found in cluster

**Solution:**
```bash
# Ensure Docker points to Minikube daemon
eval $(minikube docker-env)

# Verify environment
docker ps | grep k8s

# Rebuild images in correct environment
make build-all
```

### Issue 4: Network Connectivity Issues

**Problem:** Services can't communicate within cluster

**Diagnosis:**
```bash
# Check DNS resolution
kubectl run debug --rm -i --tty --image=nicolaka/netshoot -- bash
# Inside pod: nslookup kubernetes.default.svc.cluster.local

# Check service endpoints
kubectl get endpoints -A

# Verify network policies
kubectl get networkpolicies -A
```

**Solution:**
```bash
# Restart CoreDNS if needed
kubectl rollout restart deployment/coredns -n kube-system

# Verify cluster networking
minikube addons enable ingress
```

## Systematic Troubleshooting Process

### 1. Initial Health Check
```bash
#!/bin/bash
echo "=== Minikube Cluster Health Check ==="

# Check Minikube status
echo "1. Checking Minikube status..."
minikube status

# Check node readiness
echo "2. Checking node status..."
kubectl get nodes -o wide

# Check system pods
echo "3. Checking system pods..."
kubectl get pods -n kube-system

# Check storage classes
echo "4. Checking storage classes..."
kubectl get storageclass

# Check API server accessibility
echo "5. Testing API server..."
kubectl get componentstatuses

echo "=== Health check complete ==="
```

### 2. Component-Specific Diagnostics

#### API Server Issues
```bash
# Check API server logs
minikube logs | grep apiserver

# Verify certificates
kubectl config view --raw | grep certificate-authority-data | head -1 | cut -d' ' -f6 | base64 -d | openssl x509 -text -noout

# Test API connectivity
kubectl get --raw /healthz
```

#### Storage Issues
```bash
# List available storage classes
kubectl get storageclass

# Test PVC creation
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

# Check PVC status
kubectl get pvc test-pvc

# Cleanup
kubectl delete pvc test-pvc
```

#### Networking Issues
```bash
# Test pod-to-pod communication
kubectl run test-pod-1 --image=busybox --rm -i --tty -- sh
kubectl run test-pod-2 --image=busybox --rm -i --tty -- sh
# From pod 1: ping <pod-2-ip>

# Test service discovery
kubectl run test-client --image=busybox --rm -i --tty -- sh
# From client: nslookup kubernetes.default
```

## Prevention Strategies

### 1. Automated Cluster Validation
```bash
#!/bin/bash
# cluster-validation.sh

set -e

echo "Starting cluster validation..."

# Wait for API server
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Validate core components
kubectl get pods -n kube-system --field-selector=status.phase!=Running
if [ $? -eq 0 ]; then
    echo "Warning: Some system pods are not running"
fi

# Validate storage
kubectl get storageclass | grep default
if [ $? -ne 0 ]; then
    echo "Error: Default storage class not found"
    exit 1
fi

# Test resource creation
kubectl apply --dry-run=client -f kubernetes/infrastructure/ > /dev/null
if [ $? -ne 0 ]; then
    echo "Error: Kubernetes manifests validation failed"
    exit 1
fi

echo "Cluster validation successful!"
```

### 2. Resource Monitoring
```bash
# Create monitoring script
#!/bin/bash
# monitor-resources.sh

while true; do
    echo "=== $(date) ==="
    echo "Node resources:"
    kubectl top nodes 2>/dev/null || echo "Metrics not available"
    echo "Pod resources:"
    kubectl top pods -A 2>/dev/null || echo "Metrics not available"
    echo "Cluster events:"
    kubectl get events --sort-by='.lastTimestamp' -A | tail -5
    sleep 30
done
```

### 3. Automated Recovery
```bash
#!/bin/bash
# cluster-recovery.sh

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $(($RETRY_COUNT + 1)): Checking cluster health..."
    
    if kubectl get nodes > /dev/null 2>&1; then
        echo "Cluster is healthy"
        break
    else
        echo "Cluster unhealthy, attempting recovery..."
        minikube stop
        sleep 10
        minikube start --memory=4096 --cpus=2 --disk-size=20gb
        sleep 30
        RETRY_COUNT=$(($RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Failed to recover cluster after $MAX_RETRIES attempts"
    exit 1
fi
```

## Best Practices for ChatDB Deployment

### 1. Cluster Initialization
- Always specify resource requirements explicitly
- Use consistent configuration across environments
- Validate cluster health before proceeding with deployments

### 2. Resource Management
- Monitor resource usage regularly
- Set appropriate resource requests/limits in manifests
- Use horizontal pod autoscaling for variable workloads

### 3. Troubleshooting Workflow
1. Check Minikube status first
2. Verify API server connectivity
3. Validate storage classes
4. Test network connectivity
5. Check application-specific issues

### 4. Environment Consistency
- Use Docker environment variables consistently
- Document image build process
- Maintain version compatibility

## Quick Reference Commands

### Emergency Recovery
```bash
# Nuclear option - complete reset
minikube delete
minikube start --memory=8192 --cpus=4 --disk-size=20g
make deploy-all

# Soft restart
minikube stop && minikube start
kubectl rollout restart deployment -A

# Service-specific restart
kubectl rollout restart deployment/training-orchestrator -n chatdb-services
```

### Diagnostic Commands
```bash
# Comprehensive status check
minikube status
kubectl get nodes
kubectl get pods -A
kubectl get events --sort-by='.lastTimestamp' -A | tail -10

# Resource usage
kubectl top nodes
kubectl top pods -A

# Network diagnostics
kubectl run netshoot --rm -i --tty --image=nicolaka/netshoot -- bash
```

This troubleshooting guide should be used alongside the main deployment guide to ensure reliable ChatDB cluster operations.