#!/bin/bash

set -e

echo "🚀 Setting up ChatDB Minikube Cluster"

# Start Minikube with optimal settings
echo "📦 Starting Minikube..."
minikube start \
  --cpus=4 \
  --memory=8192 \
  --disk-size=20g \
  --driver=docker \
  --kubernetes-version=v1.28.0

# Enable required addons
echo "🔧 Enabling Minikube addons..."
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable dashboard

# Configure Docker environment
echo "🐳 Configuring Docker environment..."
eval $(minikube docker-env)

echo "✅ Minikube cluster ready!"
echo "💡 Use 'eval \$(minikube docker-env)' to configure Docker"
echo "🌐 Access dashboard: minikube dashboard"