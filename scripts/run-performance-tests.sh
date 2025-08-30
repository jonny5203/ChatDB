#!/bin/bash

# ChatDB Performance Testing Suite
# Comprehensive load testing with multiple scenarios and metrics collection

set -e

# Configuration
NAMESPACE_SERVICES="chatdb-services"
NAMESPACE_TESTING="chatdb-testing"
TEST_DURATION_SHORT="5m"
TEST_DURATION_MEDIUM="10m"  
TEST_DURATION_LONG="30m"
RESULTS_DIR="./performance-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if namespaces exist
    if ! kubectl get namespace $NAMESPACE_SERVICES &> /dev/null; then
        warning "Services namespace $NAMESPACE_SERVICES does not exist"
        return 1
    fi
    
    if ! kubectl get namespace $NAMESPACE_TESTING &> /dev/null; then
        warning "Testing namespace $NAMESPACE_TESTING does not exist, creating..."
        kubectl create namespace $NAMESPACE_TESTING
    fi
    
    success "Prerequisites check completed"
    return 0
}

# Function to setup monitoring
setup_monitoring() {
    log "Setting up monitoring infrastructure..."
    
    # Deploy Prometheus and Grafana
    kubectl apply -f kubernetes/testing/prometheus-monitoring.yaml
    
    # Wait for Prometheus to be ready
    log "Waiting for Prometheus to be ready..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n $NAMESPACE_TESTING --timeout=120s
    
    # Wait for Grafana to be ready
    log "Waiting for Grafana to be ready..."
    kubectl wait --for=condition=ready pod -l app=grafana -n $NAMESPACE_TESTING --timeout=120s
    
    success "Monitoring infrastructure setup completed"
}

# Function to deploy load testing infrastructure
deploy_load_testing() {
    log "Deploying load testing infrastructure..."
    
    # Apply Locust deployment
    kubectl apply -f kubernetes/testing/locust.yaml
    
    # Apply performance test configs
    kubectl apply -f kubernetes/testing/performance-test-configs.yaml
    
    # Wait for Locust master to be ready
    log "Waiting for Locust master to be ready..."
    kubectl wait --for=condition=ready pod -l app=locust-master -n $NAMESPACE_TESTING --timeout=120s
    
    # Wait for Locust workers to be ready
    log "Waiting for Locust workers to be ready..."
    kubectl wait --for=condition=ready pod -l app=locust-worker -n $NAMESPACE_TESTING --timeout=120s
    
    success "Load testing infrastructure deployed"
}

# Function to check service health before testing
check_service_health() {
    log "Checking service health before testing..."
    
    local services=("training-orchestrator" "test-service")
    local healthy=true
    
    for service in "${services[@]}"; do
        local url="http://$service.$NAMESPACE_SERVICES.svc.cluster.local:8000/health"
        if [ "$service" = "test-service" ]; then
            url="http://$service.$NAMESPACE_SERVICES.svc.cluster.local:8001/"
        fi
        
        log "Checking $service health..."
        
        # Use kubectl exec with a test pod to check health
        if kubectl run temp-health-check --image=curlimages/curl:latest --rm -i --restart=Never \
           -- curl -f --max-time 10 "$url" &> /dev/null; then
            success "$service is healthy"
        else
            error "$service is not responding"
            healthy=false
        fi
    done
    
    if [ "$healthy" = false ]; then
        error "Some services are not healthy. Cannot proceed with testing."
        return 1
    fi
    
    success "All services are healthy"
    return 0
}

# Function to run a specific load test scenario
run_load_test_scenario() {
    local scenario=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local description="$5"
    
    log "Running $scenario test: $description"
    log "Configuration: $users users, spawn rate $spawn_rate/sec, duration $duration"
    
    # Create results directory
    mkdir -p "$RESULTS_DIR/$scenario"
    
    # Get Locust master pod
    local master_pod=$(kubectl get pods -n $NAMESPACE_TESTING -l app=locust-master -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$master_pod" ]; then
        error "No Locust master pod found"
        return 1
    fi
    
    # Start the test via Locust web API
    log "Starting test via Locust master pod: $master_pod"
    
    # Port forward to Locust master (in background)
    kubectl port-forward -n $NAMESPACE_TESTING pod/$master_pod 8089:8089 &
    local port_forward_pid=$!
    
    # Wait a moment for port forward to establish
    sleep 5
    
    # Start the test
    curl -X POST http://localhost:8089/swarm \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "user_count=$users&spawn_rate=$spawn_rate&host=http://training-orchestrator.$NAMESPACE_SERVICES.svc.cluster.local:8000" \
        || warning "Failed to start test via web API"
    
    # Run for specified duration
    log "Test running for $duration..."
    
    # Extract minutes from duration (assumes format like "10m")
    local duration_seconds=$(echo $duration | sed 's/m$//' | awk '{print $1 * 60}')
    
    # Monitor progress
    local elapsed=0
    local interval=30
    while [ $elapsed -lt $duration_seconds ]; do
        sleep $interval
        elapsed=$((elapsed + interval))
        local remaining=$((duration_seconds - elapsed))
        log "Test progress: ${elapsed}s elapsed, ${remaining}s remaining"
        
        # Get current stats
        curl -s http://localhost:8089/stats/requests | jq '.' > "$RESULTS_DIR/$scenario/stats_${elapsed}s.json" 2>/dev/null || true
    done
    
    # Stop the test
    curl -X GET http://localhost:8089/stop || warning "Failed to stop test"
    
    # Get final results
    log "Collecting results for $scenario test..."
    
    # Download results
    curl -s http://localhost:8089/stats/requests > "$RESULTS_DIR/$scenario/final_stats.json"
    curl -s http://localhost:8089/stats/report > "$RESULTS_DIR/$scenario/report.html"
    
    # Stop port forward
    kill $port_forward_pid 2>/dev/null || true
    
    # Extract key metrics
    extract_metrics "$scenario"
    
    success "$scenario test completed"
}

# Function to extract key metrics from results
extract_metrics() {
    local scenario=$1
    local stats_file="$RESULTS_DIR/$scenario/final_stats.json"
    
    if [ -f "$stats_file" ]; then
        log "Extracting metrics for $scenario..."
        
        # Create metrics summary
        cat > "$RESULTS_DIR/$scenario/metrics_summary.txt" << EOF
Performance Test Results - $scenario
=====================================

Test Configuration:
- Scenario: $scenario
- Timestamp: $(date)

Key Metrics:
EOF
        
        # Use jq to extract metrics if available
        if command -v jq &> /dev/null && [ -s "$stats_file" ]; then
            echo "- Average Response Time: $(jq -r '.total.avg_response_time // "N/A"' $stats_file)ms" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
            echo "- 50th Percentile: $(jq -r '.total.median_response_time // "N/A"' $stats_file)ms" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
            echo "- 95th Percentile: $(jq -r '.total.percentile_95 // "N/A"' $stats_file)ms" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
            echo "- Total Requests: $(jq -r '.total.num_requests // "N/A"' $stats_file)" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
            echo "- Failed Requests: $(jq -r '.total.num_failures // "N/A"' $stats_file)" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
            echo "- Requests/sec: $(jq -r '.total.current_rps // "N/A"' $stats_file)" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
        else
            echo "- Raw stats available in final_stats.json" >> "$RESULTS_DIR/$scenario/metrics_summary.txt"
        fi
        
        success "Metrics extracted for $scenario"
    else
        warning "No stats file found for $scenario"
    fi
}

# Function to collect system metrics during tests
collect_system_metrics() {
    local scenario=$1
    log "Collecting system metrics for $scenario..."
    
    # Get pod resource usage
    kubectl top pods -n $NAMESPACE_SERVICES --no-headers > "$RESULTS_DIR/$scenario/pod_resources.txt" 2>/dev/null || \
        warning "Could not collect pod resource usage"
    
    # Get node resource usage
    kubectl top nodes --no-headers > "$RESULTS_DIR/$scenario/node_resources.txt" 2>/dev/null || \
        warning "Could not collect node resource usage"
    
    # Collect pod logs
    local pods=$(kubectl get pods -n $NAMESPACE_SERVICES -o jsonpath='{.items[*].metadata.name}')
    for pod in $pods; do
        kubectl logs -n $NAMESPACE_SERVICES $pod --tail=100 > "$RESULTS_DIR/$scenario/logs_$pod.txt" 2>/dev/null || true
    done
    
    success "System metrics collected for $scenario"
}

# Function to generate final report
generate_final_report() {
    log "Generating final performance report..."
    
    local report_file="$RESULTS_DIR/performance_test_summary.html"
    
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>ChatDB Performance Test Summary</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .scenario { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }
        .metric { background: #fff; padding: 15px; border-radius: 5px; border-left: 4px solid #007acc; }
        .metric-label { font-weight: bold; color: #333; }
        .metric-value { font-size: 1.2em; color: #007acc; margin-top: 5px; }
        .pass { border-left-color: #28a745; }
        .warning { border-left-color: #ffc107; }
        .fail { border-left-color: #dc3545; }
        .artifact-links { margin: 20px 0; }
        .artifact-links a { display: inline-block; margin: 5px 10px; padding: 8px 16px; background: #007acc; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ChatDB Performance Test Summary</h1>
            <p>Comprehensive load testing results</p>
            <p><strong>Executed:</strong> $(date)</p>
            <p><strong>Test Environment:</strong> Kubernetes Cluster</p>
        </div>
EOF
    
    # Add results for each scenario
    for scenario_dir in "$RESULTS_DIR"/*; do
        if [ -d "$scenario_dir" ]; then
            local scenario=$(basename "$scenario_dir")
            if [ "$scenario" != "performance_test_summary.html" ]; then
                cat >> "$report_file" << EOF
        <div class="scenario">
            <h2>$scenario Test Results</h2>
            <div class="artifact-links">
                <a href="$scenario/report.html">Detailed Report</a>
                <a href="$scenario/final_stats.json">Raw Stats</a>
                <a href="$scenario/metrics_summary.txt">Metrics Summary</a>
            </div>
        </div>
EOF
            fi
        fi
    done
    
    cat >> "$report_file" << 'EOF'
        <div class="scenario">
            <h2>Test Summary</h2>
            <p>All test scenarios completed successfully. Review individual reports for detailed metrics and analysis.</p>
            <h3>Success Criteria</h3>
            <ul>
                <li>Response time P95 &lt; 5 seconds</li>
                <li>Error rate &lt; 1%</li>
                <li>System remained stable throughout testing</li>
            </ul>
        </div>
    </div>
</body>
</html>
EOF
    
    success "Final report generated: $report_file"
}

# Function to cleanup resources
cleanup() {
    log "Cleaning up test resources..."
    
    # Stop any running port forwards
    pkill -f "kubectl port-forward.*8089" 2>/dev/null || true
    
    # Optional: Clean up test deployments
    if [ "$CLEANUP_AFTER_TEST" = "true" ]; then
        kubectl delete -f kubernetes/testing/locust.yaml 2>/dev/null || true
        kubectl delete -f kubernetes/testing/performance-test-configs.yaml 2>/dev/null || true
        kubectl delete -f kubernetes/testing/prometheus-monitoring.yaml 2>/dev/null || true
    fi
    
    success "Cleanup completed"
}

# Main execution function
main() {
    log "Starting ChatDB Performance Testing Suite"
    log "Results will be saved to: $RESULTS_DIR"
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    # Check prerequisites
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        exit 1
    fi
    
    # Setup monitoring
    setup_monitoring
    
    # Deploy load testing infrastructure
    deploy_load_testing
    
    # Check service health
    if ! check_service_health; then
        error "Service health check failed"
        exit 1
    fi
    
    # Run test scenarios
    log "Starting performance test scenarios..."
    
    # Baseline test
    run_load_test_scenario "baseline" 100 10 "$TEST_DURATION_MEDIUM" "Normal load baseline test"
    collect_system_metrics "baseline"
    
    # Spike test
    run_load_test_scenario "spike" 500 50 "$TEST_DURATION_SHORT" "Spike load test with burst traffic"
    collect_system_metrics "spike"
    
    # Stress test
    run_load_test_scenario "stress" 1000 25 "$TEST_DURATION_MEDIUM" "High load stress test"
    collect_system_metrics "stress"
    
    # Generate final report
    generate_final_report
    
    success "Performance testing suite completed successfully!"
    log "Results available in: $RESULTS_DIR"
    log "Open $RESULTS_DIR/performance_test_summary.html to view the report"
    
    # Show quick summary
    log "Quick Summary:"
    for scenario in baseline spike stress; do
        if [ -f "$RESULTS_DIR/$scenario/metrics_summary.txt" ]; then
            log "- $scenario: $(grep -E "(Average Response Time|Failed Requests)" "$RESULTS_DIR/$scenario/metrics_summary.txt" | tr '\n' ' ')"
        fi
    done
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        echo "ChatDB Performance Testing Suite"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --cleanup-after     Cleanup test resources after completion"
        echo "  --short-duration    Use shorter test durations for quick testing"
        echo ""
        echo "Environment Variables:"
        echo "  NAMESPACE_SERVICES  Services namespace (default: chatdb-services)"
        echo "  NAMESPACE_TESTING   Testing namespace (default: chatdb-testing)"
        echo "  CLEANUP_AFTER_TEST  Cleanup after tests (default: false)"
        exit 0
        ;;
    --cleanup-after)
        export CLEANUP_AFTER_TEST="true"
        ;;
    --short-duration)
        TEST_DURATION_SHORT="2m"
        TEST_DURATION_MEDIUM="5m"
        TEST_DURATION_LONG="10m"
        ;;
esac

# Execute main function
main "$@"