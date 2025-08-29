#!/bin/bash

set -e

echo "🐳 Building ChatDB Docker images for Minikube"

# Configure Docker to use Minikube's Docker daemon
eval $(minikube docker-env)

# Build all service images
echo "🔨 Building training-orchestrator..."
docker build -t chatdb/training-orchestrator:latest ./training-orchestrator

echo "🔨 Building query-parser..."
docker build -t chatdb/query-parser:latest ./query-parser

echo "🔨 Building ml-engine..."
docker build -t chatdb/ml-engine:latest ./ml_engine

echo "🔨 Building model-registry..."
docker build -t chatdb/model-registry:latest ./model-registry

echo "🔨 Building test-service..."
docker build -t chatdb/test-service:latest ./test-service

echo "✅ All images built successfully!"
echo "📋 Images available in Minikube:"
docker images | grep chatdb