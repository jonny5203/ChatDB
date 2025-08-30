# ChatDB Makefile for Kubernetes Deployment and Testing

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ==================== Environment Setup ====================

.PHONY: setup-minikube
setup-minikube: ## Start and configure Minikube cluster
	@echo "Starting Minikube cluster..."
	minikube start --cpus=4 --memory=8192 --disk-size=20g --driver=docker
	minikube addons enable ingress
	minikube addons enable metrics-server
	minikube addons enable dashboard
	@echo "Minikube cluster ready!"

.PHONY: setup-env
setup-env: ## Set up local environment
	@echo "Setting up environment..."
	eval $$(minikube docker-env)
	@echo "Environment configured for Minikube Docker daemon"

# ==================== Build ====================

.PHONY: build-all
build-all: build-training-orchestrator build-query-parser build-ml-engine build-model-registry build-test-service ## Build all service images

.PHONY: build-training-orchestrator
build-training-orchestrator: ## Build training orchestrator image
	@echo "Building training-orchestrator..."
	docker build -t chatdb/training-orchestrator:latest ./training-orchestrator

.PHONY: build-query-parser
build-query-parser: ## Build query parser image
	@echo "Building query-parser..."
	docker build -t chatdb/query-parser:latest ./query-parser

.PHONY: build-ml-engine
build-ml-engine: ## Build ML engine image
	@echo "Building ml-engine..."
	docker build -t chatdb/ml-engine:latest ./ml_engine

.PHONY: build-model-registry
build-model-registry: ## Build model registry image
	@echo "Building model-registry..."
	docker build -t chatdb/model-registry:latest ./model-registry

.PHONY: build-test-service
build-test-service: ## Build test service image
	@echo "Building test-service..."
	docker build -t chatdb/test-service:latest ./test-service

# ==================== Kubernetes Deployment ====================

.PHONY: create-namespaces
create-namespaces: ## Create Kubernetes namespaces
	kubectl create namespace chatdb-system --dry-run=client -o yaml | kubectl apply -f -
	kubectl create namespace chatdb-services --dry-run=client -o yaml | kubectl apply -f -
	kubectl create namespace chatdb-monitoring --dry-run=client -o yaml | kubectl apply -f -
	kubectl create namespace chatdb-testing --dry-run=client -o yaml | kubectl apply -f -

.PHONY: deploy-infrastructure
deploy-infrastructure: create-namespaces ## Deploy infrastructure services (PostgreSQL, Kafka)
	@echo "Deploying infrastructure services..."
	kubectl apply -f kubernetes/infrastructure/

.PHONY: deploy-services
deploy-services: ## Deploy application services
	@echo "Deploying application services..."
	kubectl apply -f kubernetes/services/

.PHONY: deploy-monitoring
deploy-monitoring: ## Deploy monitoring stack (Prometheus, Grafana)
	@echo "Deploying monitoring stack..."
	kubectl apply -f kubernetes/monitoring/

.PHONY: deploy-all
deploy-all: deploy-infrastructure wait-infrastructure deploy-services deploy-monitoring ## Deploy entire application stack
	@echo "All services deployed successfully!"

.PHONY: wait-infrastructure
wait-infrastructure: ## Wait for infrastructure services to be ready
	@echo "Waiting for PostgreSQL..."
	kubectl wait --for=condition=ready pod -l app=postgres -n chatdb-system --timeout=300s
	@echo "Waiting for Kafka..."
	kubectl wait --for=condition=ready pod -l app=kafka -n chatdb-system --timeout=300s

# ==================== Testing ====================

.PHONY: test-unit
test-unit: ## Run unit tests for all services
	@echo "Running unit tests..."
	cd training-orchestrator && pytest tests/
	cd query-parser && pytest tests/
	cd ml_engine && pytest tests/
	cd model-registry && pytest tests/

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "Running integration tests..."
	kubectl apply -f kubernetes/testing/test-runner.yaml
	kubectl wait --for=condition=ready pod -l app=test-runner -n chatdb-testing --timeout=60s
	kubectl exec -it -n chatdb-testing $$(kubectl get pod -l app=test-runner -n chatdb-testing -o name) -- pytest /tests/integration/ -v

.PHONY: test-load
test-load: ## Run comprehensive load tests with multiple scenarios
	@echo "Running comprehensive load tests..."
	./scripts/run-performance-tests.sh

.PHONY: test-load-quick
test-load-quick: ## Run quick load tests with shorter duration
	@echo "Running quick load tests..."
	./scripts/run-performance-tests.sh --short-duration

.PHONY: test-load-interactive
test-load-interactive: ## Start interactive Locust for manual testing
	@echo "Starting interactive load test environment..."
	kubectl apply -f kubernetes/testing/locust.yaml
	kubectl wait --for=condition=ready pod -l app=locust-master -n chatdb-testing --timeout=60s
	@echo "Locust UI available at: http://localhost:8089"
	kubectl port-forward -n chatdb-testing svc/locust-master 8089:8089

.PHONY: setup-performance-monitoring
setup-performance-monitoring: ## Setup Prometheus and Grafana for performance monitoring
	@echo "Setting up performance monitoring..."
	kubectl apply -f kubernetes/testing/prometheus-monitoring.yaml
	kubectl wait --for=condition=ready pod -l app=prometheus -n chatdb-testing --timeout=120s
	kubectl wait --for=condition=ready pod -l app=grafana -n chatdb-testing --timeout=120s
	@echo "Monitoring setup complete!"
	@echo "Grafana available at: http://localhost:3000 (admin/admin)"
	@echo "Prometheus available at: http://localhost:9090"

.PHONY: test-chaos
test-chaos: ## Run comprehensive chaos engineering tests
	@echo "Running comprehensive chaos engineering tests..."
	./scripts/chaos-testing-suite.sh

.PHONY: test-chaos-install
test-chaos-install: ## Install Chaos Mesh only
	@echo "Installing Chaos Mesh..."
	./scripts/chaos-testing-suite.sh --install-only

.PHONY: test-chaos-pods
test-chaos-pods: ## Run pod failure chaos tests only
	@echo "Running pod failure chaos tests..."
	./scripts/chaos-testing-suite.sh --experiment pod-failures

.PHONY: test-chaos-network
test-chaos-network: ## Run network chaos tests only
	@echo "Running network chaos tests..."
	./scripts/chaos-testing-suite.sh --experiment network-chaos

.PHONY: test-chaos-stress
test-chaos-stress: ## Run resource stress tests only
	@echo "Running resource stress tests..."
	./scripts/chaos-testing-suite.sh --experiment resource-stress

.PHONY: test-chaos-cleanup
test-chaos-cleanup: ## Clean up all chaos experiments
	@echo "Cleaning up chaos experiments..."
	./scripts/chaos-testing-suite.sh --cleanup

.PHONY: chaos-dashboard
chaos-dashboard: ## Access Chaos Mesh dashboard
	@echo "Chaos Mesh dashboard available at: http://localhost:2333"
	kubectl port-forward -n chaos-testing svc/chaos-dashboard 2333:2333

.PHONY: test-robustness
test-robustness: ## Run robustness test suite
	@echo "Running robustness tests..."
	./scripts/test-robustness.sh

.PHONY: test-all
test-all: test-unit test-integration test-load ## Run all tests

.PHONY: setup-test-reporting
setup-test-reporting: ## Setup comprehensive test result aggregation and reporting
	@echo "Setting up test result aggregation and reporting..."
	kubectl apply -f kubernetes/testing/test-results-aggregation.yaml
	kubectl wait --for=condition=ready pod -l app=test-results-collector -n chatdb-testing --timeout=120s
	kubectl wait --for=condition=ready pod -l app=test-results-web -n chatdb-testing --timeout=120s
	@echo "Test reporting setup complete!"
	@echo "Test results web interface will be available at: http://localhost:8080"

.PHONY: setup-test-dashboard
setup-test-dashboard: ## Setup Grafana dashboard for test metrics visualization
	@echo "Setting up test metrics dashboard..."
	kubectl apply -f kubernetes/testing/grafana-test-dashboard.yaml
	kubectl wait --for=condition=ready pod -l app=test-metrics-exporter -n chatdb-testing --timeout=120s
	@echo "Test dashboard setup complete!"
	@echo "Metrics available at: http://localhost:8000/metrics"

.PHONY: collect-test-results
collect-test-results: ## Manually collect and aggregate test results
	@echo "Collecting test results..."
	kubectl exec -n chatdb-testing deployment/test-results-collector -- /scripts/collect-results.sh
	@echo "Results collection completed"

.PHONY: view-test-results
view-test-results: ## Access test results web interface
	@echo "Test results available at: http://localhost:8080"
	kubectl port-forward -n chatdb-testing svc/test-results-web 8080:8080

.PHONY: view-test-metrics
view-test-metrics: ## Access test metrics endpoint
	@echo "Test metrics available at: http://localhost:8000/metrics"
	kubectl port-forward -n chatdb-testing svc/test-metrics-exporter 8000:8000

.PHONY: test-complete-suite
test-complete-suite: ## Run complete testing suite with result collection
	@echo "Running complete ChatDB testing suite..."
	@echo "This will execute: Unit → Integration → Load → Chaos → Results Collection"
	make test-unit
	make test-integration  
	make test-load-quick
	make test-chaos-pods --duration=60s
	make collect-test-results
	@echo "Complete testing suite finished!"
	@echo "View results: make view-test-results"

# ==================== Monitoring ====================

.PHONY: port-forward-grafana
port-forward-grafana: ## Access Grafana dashboard (admin/admin)
	@echo "Grafana available at: http://localhost:3000"
	kubectl port-forward -n chatdb-monitoring svc/grafana 3000:3000

.PHONY: port-forward-prometheus
port-forward-prometheus: ## Access Prometheus UI
	@echo "Prometheus available at: http://localhost:9090"
	kubectl port-forward -n chatdb-monitoring svc/prometheus 9090:9090

.PHONY: port-forward-jaeger
port-forward-jaeger: ## Access Jaeger tracing UI
	@echo "Jaeger available at: http://localhost:16686"
	kubectl port-forward -n chatdb-monitoring svc/jaeger-query 16686:16686

.PHONY: port-forward-kibana
port-forward-kibana: ## Access Kibana logging UI
	@echo "Kibana available at: http://localhost:5601"
	kubectl port-forward -n chatdb-monitoring svc/kibana 5601:5601

# ==================== Management ====================

.PHONY: status
status: ## Check status of all deployments
	@echo "=== Namespace: chatdb-system ==="
	kubectl get pods -n chatdb-system
	@echo "\n=== Namespace: chatdb-services ==="
	kubectl get pods -n chatdb-services
	@echo "\n=== Services ==="
	kubectl get svc -A | grep chatdb

.PHONY: logs
logs: ## Tail logs from all services
	kubectl logs -f -n chatdb-services -l app=chatdb --all-containers=true --prefix=true

.PHONY: logs-training
logs-training: ## View training orchestrator logs
	kubectl logs -f -n chatdb-services deployment/training-orchestrator

.PHONY: logs-kafka
logs-kafka: ## View Kafka logs
	kubectl logs -f -n chatdb-system statefulset/kafka

.PHONY: scale
scale: ## Scale a service (usage: make scale SERVICE=training-orchestrator REPLICAS=3)
	kubectl scale deployment/$(SERVICE) -n chatdb-services --replicas=$(REPLICAS)

.PHONY: restart
restart: ## Restart all services
	kubectl rollout restart deployment -n chatdb-services

.PHONY: clean-pods
clean-pods: ## Delete failed/evicted pods
	kubectl delete pods --field-selector status.phase=Failed -A
	kubectl delete pods --field-selector status.phase=Evicted -A

# ==================== Cleanup ====================

.PHONY: delete-services
delete-services: ## Delete application services
	kubectl delete -f kubernetes/services/ --ignore-not-found=true

.PHONY: delete-infrastructure
delete-infrastructure: ## Delete infrastructure services
	kubectl delete -f kubernetes/infrastructure/ --ignore-not-found=true

.PHONY: delete-monitoring
delete-monitoring: ## Delete monitoring stack
	kubectl delete -f kubernetes/monitoring/ --ignore-not-found=true

.PHONY: delete-all
delete-all: delete-services delete-infrastructure delete-monitoring ## Delete all deployments
	kubectl delete namespace chatdb-system chatdb-services chatdb-monitoring chatdb-testing --ignore-not-found=true

.PHONY: clean
clean: delete-all ## Complete cleanup including Minikube
	minikube delete

# ==================== Development ====================

.PHONY: dev-tunnel
dev-tunnel: ## Create tunnel to services (for development)
	minikube tunnel

.PHONY: dashboard
dashboard: ## Open Kubernetes dashboard
	minikube dashboard

.PHONY: shell
shell: ## Get shell access to a pod (usage: make shell POD=training-orchestrator)
	kubectl exec -it -n chatdb-services deployment/$(POD) -- /bin/bash

.PHONY: debug
debug: ## Debug a service (usage: make debug SERVICE=training-orchestrator PORT=8000)
	kubectl port-forward -n chatdb-services deployment/$(SERVICE) $(PORT):$(PORT)

# ==================== Helm ====================

.PHONY: helm-install
helm-install: ## Install ChatDB using Helm chart
	helm install chatdb ./helm/chatdb -n chatdb-services --create-namespace

.PHONY: helm-upgrade
helm-upgrade: ## Upgrade ChatDB Helm release
	helm upgrade chatdb ./helm/chatdb -n chatdb-services

.PHONY: helm-uninstall
helm-uninstall: ## Uninstall ChatDB Helm release
	helm uninstall chatdb -n chatdb-services

# ==================== Utilities ====================

.PHONY: validate
validate: ## Validate Kubernetes manifests
	kubectl apply --dry-run=client -f kubernetes/

.PHONY: lint
lint: ## Lint Kubernetes manifests
	yamllint kubernetes/

.PHONY: format
format: ## Format YAML files
	prettier --write "kubernetes/**/*.yaml"

# Default target
.DEFAULT_GOAL := help