#!/bin/bash

set -e

echo "🚀 Deploying ChatDB to Kubernetes"

# Create namespaces
echo "📁 Creating namespaces..."
kubectl create namespace chatdb-system --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace chatdb-services --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace chatdb-monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace chatdb-testing --dry-run=client -o yaml | kubectl apply -f -

# Label namespaces for network policies
kubectl label namespace chatdb-system name=chatdb-system --overwrite
kubectl label namespace chatdb-services name=chatdb-services --overwrite

# Deploy infrastructure (order matters)
echo "🏗️  Deploying infrastructure..."
kubectl apply -f kubernetes/infrastructure/postgres.yaml
kubectl apply -f kubernetes/infrastructure/minio.yaml
kubectl apply -f kubernetes/infrastructure/kafka.yaml

# Wait for infrastructure
echo "⏳ Waiting for infrastructure..."
kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n chatdb-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=kafka -n chatdb-system --timeout=300s

# Deploy services
echo "🚀 Deploying services..."
kubectl apply -f kubernetes/services/

# Wait for services
echo "⏳ Waiting for services..."
kubectl wait --for=condition=ready pod -l app=training-orchestrator -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=model-registry -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=query-parser -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=ml-engine -n chatdb-services --timeout=300s
kubectl wait --for=condition=ready pod -l app=test-service -n chatdb-services --timeout=300s

echo "✅ Deployment complete!"
echo "🔍 Check service status: kubectl get pods -n chatdb-services"
echo "🌐 Access services using kubectl port-forward"
echo "📊 Dashboard: minikube dashboard"