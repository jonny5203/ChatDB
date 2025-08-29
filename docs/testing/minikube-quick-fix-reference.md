# Minikube Quick Fix Reference

## Emergency Commands

### 🚨 Critical: API Server Down
```bash
# Symptoms: "dial tcp [::1]:8443: connect: connection refused"
minikube delete
minikube start --memory=4096 --cpus=2 --disk-size=20gb
```

### 🔧 Quick Health Check
```bash
minikube status && kubectl get nodes && kubectl get storageclass
```

### 🔄 Complete Reset
```bash
minikube delete
minikube start --memory=8192 --cpus=4 --disk-size=20g
eval $(minikube docker-env)
make build-all && make deploy-all
```

## Common Error Patterns & Fixes

| Error Message | Quick Fix |
|---------------|-----------|
| `apiserver: Stopped` | `minikube delete && minikube start` |
| `cannot change memory size` | `minikube delete` first |
| `failed to download openapi` | Recreation required |
| `imagePullPolicy: Never` needed | `eval $(minikube docker-env)` |
| Storage provisioner errors | Cluster recreation |
| DNS resolution failures | `kubectl rollout restart deployment/coredns -n kube-system` |

## Diagnostic Commands

### System Status
```bash
minikube status                                    # Cluster components
kubectl get nodes                                  # Node readiness
kubectl get pods -n kube-system                    # System pods
kubectl get storageclass                           # Storage
```

### Resource Usage
```bash
kubectl top nodes                                  # Node resources
kubectl top pods -A                                # Pod resources
kubectl get events --sort-by='.lastTimestamp' -A   # Recent events
```

### Service Health
```bash
kubectl get pods -A | grep -v Running              # Failed pods
kubectl get svc -A | grep chatdb                   # Services
make status                                        # ChatDB status
```

## Recovery Procedures

### 1. Soft Recovery
```bash
minikube stop && minikube start
kubectl rollout restart deployment -A
```

### 2. Image Recovery
```bash
eval $(minikube docker-env)
make build-all
kubectl rollout restart deployment -n chatdb-services
```

### 3. Hard Recovery
```bash
minikube delete
minikube start --memory=8192 --cpus=4 --disk-size=20g
eval $(minikube docker-env)
make build-all
make deploy-all
```

## Validation Checklist

- [ ] `minikube status` shows all components running
- [ ] `kubectl get nodes` shows Ready status
- [ ] `kubectl get storageclass` shows default class
- [ ] `docker images | grep chatdb` shows built images
- [ ] `make status` shows all pods running
- [ ] Health endpoints respond correctly

## Support Resources

- **Detailed Guide**: [minikube-troubleshooting-guide.md](./minikube-troubleshooting-guide.md)
- **Full Deployment**: [minikube-deployment-guide.md](./minikube-deployment-guide.md)
- **Test Reference**: [quick-test-reference.md](./quick-test-reference.md)