#!/bin/bash

# Training Orchestrator Kubernetes Test Runner
# This script executes comprehensive tests for the Training Orchestrator service

set -e

echo "🚀 Starting Training Orchestrator Kubernetes Tests"
echo "================================================="

# Set environment variables with defaults
export TRAINING_ORCHESTRATOR_URL="${TRAINING_ORCHESTRATOR_URL:-http://training-orchestrator.default.svc.cluster.local:8000}"
export DATABASE_HOST="${DATABASE_HOST:-postgres.default.svc.cluster.local}"
export DATABASE_PORT="${DATABASE_PORT:-5432}"
export DATABASE_NAME="${DATABASE_NAME:-training_db}"
export DATABASE_USER="${DATABASE_USER:-user}"
export DATABASE_PASSWORD="${DATABASE_PASSWORD:-password}"

echo "📋 Test Configuration:"
echo "  Service URL: $TRAINING_ORCHESTRATOR_URL"
echo "  Database: $DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo ""

# Create test results directory
mkdir -p test-results

# Wait for services to be ready
echo "⏳ Waiting for Training Orchestrator service..."
timeout 60 bash -c 'until curl -s "$TRAINING_ORCHESTRATOR_URL/health" > /dev/null; do sleep 2; done' || {
    echo "❌ Training Orchestrator service not responding after 60 seconds"
    exit 1
}

echo "⏳ Waiting for Database service..."
timeout 30 bash -c 'until nc -z "$DATABASE_HOST" "$DATABASE_PORT"; do sleep 2; done' || {
    echo "❌ Database service not responding after 30 seconds"
    exit 1
}

echo "✅ All services are ready!"
echo ""

# Run tests with different categories
echo "🧪 Running Training Orchestrator Tests"
echo "======================================"

# Basic health and connectivity tests
echo "Running basic connectivity tests..."
pytest -v -m "integration and kubernetes and not slow" \
    --junit-xml=test-results/basic-tests-junit.xml \
    tests/test_training_orchestrator_k8s.py::test_training_orchestrator_health \
    tests/test_training_orchestrator_k8s.py::test_service_connectivity_timeout \
    tests/test_training_orchestrator_k8s.py::test_nonexistent_job_retrieval

# Database connectivity tests
echo ""
echo "Running database connectivity tests..."
pytest -v -m "database" \
    --junit-xml=test-results/database-tests-junit.xml \
    tests/test_training_orchestrator_k8s.py::test_database_connectivity_direct \
    tests/test_training_orchestrator_k8s.py::test_training_jobs_table_exists

# Core API functionality tests
echo ""
echo "Running core API functionality tests..."
pytest -v -m "integration and kubernetes and not slow and not performance" \
    --junit-xml=test-results/api-tests-junit.xml \
    tests/test_training_orchestrator_k8s.py::test_create_training_job_k8s \
    tests/test_training_orchestrator_k8s.py::test_list_training_jobs_k8s

# Error handling tests
echo ""
echo "Running error handling tests..."
pytest -v -m "resilience or timeout" \
    --junit-xml=test-results/error-tests-junit.xml \
    tests/test_training_orchestrator_k8s.py::test_service_error_handling \
    tests/test_training_orchestrator_k8s.py::test_invalid_job_data_validation \
    tests/test_training_orchestrator_k8s.py::test_service_recovery_after_error \
    tests/test_training_orchestrator_k8s.py::test_service_timeout_handling

# Performance and lifecycle tests (if time allows)
echo ""
echo "Running performance and lifecycle tests..."
pytest -v -m "performance or slow" \
    --junit-xml=test-results/performance-tests-junit.xml \
    --timeout=300 \
    tests/test_training_orchestrator_k8s.py::test_concurrent_job_creation_limits \
    tests/test_training_orchestrator_k8s.py::test_job_lifecycle_complete || {
        echo "⚠️  Performance/lifecycle tests failed - may be expected in some environments"
    }

# Run all tests together for comprehensive coverage
echo ""
echo "Running comprehensive test suite..."
pytest -v tests/test_training_orchestrator_k8s.py \
    --junit-xml=test-results/comprehensive-junit.xml \
    --html=test-results/comprehensive-report.html \
    --self-contained-html \
    --timeout=300 || {
        echo "⚠️  Some comprehensive tests failed - check individual test results"
    }

echo ""
echo "📊 Test Results Summary"
echo "======================"

# Count test results
if [ -f "test-results/comprehensive-junit.xml" ]; then
    echo "Test results available in test-results/ directory:"
    echo "  - JUnit XML: comprehensive-junit.xml"
    echo "  - HTML Report: comprehensive-report.html"
    
    # Extract basic stats from JUnit XML if available
    if command -v xmllint >/dev/null 2>&1; then
        TESTS=$(xmllint --xpath "string(/testsuite/@tests)" test-results/comprehensive-junit.xml 2>/dev/null || echo "N/A")
        FAILURES=$(xmllint --xpath "string(/testsuite/@failures)" test-results/comprehensive-junit.xml 2>/dev/null || echo "N/A")
        ERRORS=$(xmllint --xpath "string(/testsuite/@errors)" test-results/comprehensive-junit.xml 2>/dev/null || echo "N/A")
        SKIPPED=$(xmllint --xpath "string(/testsuite/@skipped)" test-results/comprehensive-junit.xml 2>/dev/null || echo "N/A")
        
        echo "  - Tests: $TESTS"
        echo "  - Failures: $FAILURES" 
        echo "  - Errors: $ERRORS"
        echo "  - Skipped: $SKIPPED"
    fi
fi

echo ""
echo "✅ Training Orchestrator tests completed!"
echo "Check test-results/ directory for detailed reports"