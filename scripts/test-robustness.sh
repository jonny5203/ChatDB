#!/bin/bash

# ChatDB Robustness Testing Script
# Tests system resilience, fault tolerance, and recovery capabilities

set -e

NAMESPACE="chatdb-services"
REPORT_DIR="reports"
METRICS_DIR="metrics"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p $REPORT_DIR $METRICS_DIR

echo -e "${GREEN}Starting ChatDB Robustness Test Suite${NC}"
echo "================================================"

# Function to print test status
print_test() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
}

# Function to check service health
check_health() {
    local service=$1
    local port=$2
    kubectl exec -n $NAMESPACE deployment/$service -- curl -s http://localhost:$port/health > /dev/null 2>&1
    return $?
}

# Function to measure recovery time
measure_recovery() {
    local service=$1
    local port=$2
    local start_time=$(date +%s)
    
    while ! check_health $service $port; do
        sleep 1
    done
    
    local end_time=$(date +%s)
    local recovery_time=$((end_time - start_time))
    echo $recovery_time
}

# Initialize test report
cat > $REPORT_DIR/robustness-test-results.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>ChatDB Robustness Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
        .pass { background-color: #d4edda; }
        .fail { background-color: #f8d7da; }
        .metric { font-weight: bold; }
    </style>
</head>
<body>
    <h1>ChatDB Robustness Test Results</h1>
    <p>Test Date: $(date)</p>
EOF

# Test 1: Pod Failure Recovery
print_test "Pod Failure Recovery"
echo "Testing automatic recovery from pod failures..."

# Kill a pod and measure recovery
POD=$(kubectl get pod -n $NAMESPACE -l app=training-orchestrator -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD -n $NAMESPACE

echo "Waiting for pod recovery..."
RECOVERY_TIME=$(measure_recovery "training-orchestrator" "8000")

if [ $RECOVERY_TIME -lt 60 ]; then
    echo -e "${GREEN}✓ Pod recovered in ${RECOVERY_TIME}s${NC}"
    echo "<div class='test pass'>Pod Failure Recovery: PASSED (${RECOVERY_TIME}s)</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${RED}✗ Pod recovery took too long: ${RECOVERY_TIME}s${NC}"
    echo "<div class='test fail'>Pod Failure Recovery: FAILED (${RECOVERY_TIME}s)</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Test 2: Database Connection Resilience
print_test "Database Connection Resilience"
echo "Testing resilience to database connection issues..."

# Temporarily block database connection
kubectl exec -n chatdb-system deployment/postgres -- iptables -A INPUT -p tcp --dport 5432 -j DROP 2>/dev/null || true
sleep 5

# Check if service degrades gracefully
if kubectl exec -n $NAMESPACE deployment/training-orchestrator -- curl -s http://localhost:8000/health | grep -q "degraded"; then
    echo -e "${GREEN}✓ Service degraded gracefully${NC}"
    echo "<div class='test pass'>Database Resilience: PASSED (Graceful degradation)</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${YELLOW}⚠ Service did not indicate degradation${NC}"
    echo "<div class='test fail'>Database Resilience: WARNING (No degradation signal)</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Restore database connection
kubectl exec -n chatdb-system deployment/postgres -- iptables -D INPUT -p tcp --dport 5432 -j DROP 2>/dev/null || true

# Test 3: Kafka Broker Failure
print_test "Kafka Broker Failure"
echo "Testing message queue resilience..."

# Scale down Kafka
kubectl scale statefulset kafka -n chatdb-system --replicas=0
sleep 10

# Test if services handle Kafka unavailability
KAFKA_TEST_PASSED=true
for service in training-orchestrator query-parser ml-engine; do
    if ! kubectl logs -n $NAMESPACE deployment/$service --tail=10 | grep -q "Kafka connection retry"; then
        KAFKA_TEST_PASSED=false
    fi
done

# Scale Kafka back up
kubectl scale statefulset kafka -n chatdb-system --replicas=1

if $KAFKA_TEST_PASSED; then
    echo -e "${GREEN}✓ Services handled Kafka failure gracefully${NC}"
    echo "<div class='test pass'>Kafka Resilience: PASSED</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${RED}✗ Some services did not handle Kafka failure properly${NC}"
    echo "<div class='test fail'>Kafka Resilience: FAILED</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Test 4: Resource Exhaustion
print_test "Resource Exhaustion Handling"
echo "Testing behavior under resource constraints..."

# Create resource pressure
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: stress-test
  namespace: $NAMESPACE
spec:
  template:
    spec:
      containers:
      - name: stress
        image: progrium/stress
        args: ["--cpu", "8", "--vm", "2", "--vm-bytes", "128M", "--timeout", "30s"]
      restartPolicy: Never
EOF

sleep 35

# Check if services are still responsive
RESOURCE_TEST_PASSED=true
for service in training-orchestrator model-registry; do
    if ! check_health $service 8000; then
        RESOURCE_TEST_PASSED=false
    fi
done

# Clean up stress test
kubectl delete job stress-test -n $NAMESPACE

if $RESOURCE_TEST_PASSED; then
    echo -e "${GREEN}✓ Services remained responsive under resource pressure${NC}"
    echo "<div class='test pass'>Resource Exhaustion: PASSED</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${RED}✗ Some services became unresponsive${NC}"
    echo "<div class='test fail'>Resource Exhaustion: FAILED</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Test 5: Network Partition
print_test "Network Partition Tolerance"
echo "Testing network partition handling..."

# Apply network policy to isolate services
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-training-orchestrator
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: training-orchestrator
  policyTypes:
  - Ingress
  - Egress
EOF

sleep 10

# Check if service handles isolation
if kubectl logs -n $NAMESPACE deployment/training-orchestrator --tail=20 | grep -q "circuit breaker.*open"; then
    echo -e "${GREEN}✓ Circuit breaker activated during network partition${NC}"
    echo "<div class='test pass'>Network Partition: PASSED (Circuit breaker activated)</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${YELLOW}⚠ Circuit breaker did not activate${NC}"
    echo "<div class='test fail'>Network Partition: WARNING (No circuit breaker)</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Remove network policy
kubectl delete networkpolicy isolate-training-orchestrator -n $NAMESPACE

# Test 6: Cascading Failure Prevention
print_test "Cascading Failure Prevention"
echo "Testing prevention of cascading failures..."

# Overload one service
kubectl exec -n $NAMESPACE deployment/training-orchestrator -- sh -c "for i in {1..100}; do curl -X POST http://localhost:8000/jobs -d '{\"model_name\":\"test\"}' & done"

sleep 5

# Check if other services are affected
CASCADE_TEST_PASSED=true
for service in query-parser model-registry; do
    if ! check_health $service 8000; then
        CASCADE_TEST_PASSED=false
    fi
done

if $CASCADE_TEST_PASSED; then
    echo -e "${GREEN}✓ Cascading failure prevented${NC}"
    echo "<div class='test pass'>Cascading Failure Prevention: PASSED</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${RED}✗ Cascading failure occurred${NC}"
    echo "<div class='test fail'>Cascading Failure Prevention: FAILED</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Test 7: Data Consistency Check
print_test "Data Consistency Under Failure"
echo "Testing data consistency during failures..."

# Submit a job
JOB_ID=$(kubectl exec -n $NAMESPACE deployment/training-orchestrator -- \
    curl -s -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{"model_name":"consistency-test","dataset_location":"s3://test"}' | \
    jq -r '.id')

# Restart pod mid-operation
kubectl delete pod -n $NAMESPACE -l app=training-orchestrator

# Wait for recovery
sleep 30

# Check if job state is consistent
JOB_STATUS=$(kubectl exec -n $NAMESPACE deployment/training-orchestrator -- \
    curl -s http://localhost:8000/jobs/$JOB_ID | jq -r '.status')

if [ "$JOB_STATUS" != "null" ] && [ "$JOB_STATUS" != "" ]; then
    echo -e "${GREEN}✓ Data consistency maintained (Job status: $JOB_STATUS)${NC}"
    echo "<div class='test pass'>Data Consistency: PASSED</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${RED}✗ Data inconsistency detected${NC}"
    echo "<div class='test fail'>Data Consistency: FAILED</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Test 8: Autoscaling Under Load
print_test "Autoscaling Response"
echo "Testing autoscaling behavior..."

# Get initial replica count
INITIAL_REPLICAS=$(kubectl get deployment training-orchestrator -n $NAMESPACE -o jsonpath='{.spec.replicas}')

# Generate load to trigger autoscaling
kubectl run load-generator -n $NAMESPACE --image=busybox --restart=Never -- \
    sh -c "while true; do wget -q -O- http://training-orchestrator:8000/health; done"

# Wait for autoscaling
sleep 60

# Check if replicas increased
CURRENT_REPLICAS=$(kubectl get deployment training-orchestrator -n $NAMESPACE -o jsonpath='{.spec.replicas}')

kubectl delete pod load-generator -n $NAMESPACE

if [ $CURRENT_REPLICAS -gt $INITIAL_REPLICAS ]; then
    echo -e "${GREEN}✓ Autoscaling triggered (${INITIAL_REPLICAS} -> ${CURRENT_REPLICAS} replicas)${NC}"
    echo "<div class='test pass'>Autoscaling: PASSED (Scaled from ${INITIAL_REPLICAS} to ${CURRENT_REPLICAS})</div>" >> $REPORT_DIR/robustness-test-results.html
else
    echo -e "${YELLOW}⚠ Autoscaling did not trigger${NC}"
    echo "<div class='test fail'>Autoscaling: WARNING (No scaling observed)</div>" >> $REPORT_DIR/robustness-test-results.html
fi

# Generate metrics JSON
cat > $METRICS_DIR/robustness-metrics.json << EOF
{
  "test_date": "$(date -Iseconds)",
  "tests": {
    "pod_recovery_time": $RECOVERY_TIME,
    "database_resilience": $([ $? -eq 0 ] && echo "true" || echo "false"),
    "kafka_resilience": $KAFKA_TEST_PASSED,
    "resource_exhaustion": $RESOURCE_TEST_PASSED,
    "cascade_prevention": $CASCADE_TEST_PASSED,
    "data_consistency": $([ "$JOB_STATUS" != "null" ] && echo "true" || echo "false"),
    "autoscaling": $([ $CURRENT_REPLICAS -gt $INITIAL_REPLICAS ] && echo "true" || echo "false")
  },
  "summary": {
    "total_tests": 8,
    "passed": $(grep -c "PASSED" $REPORT_DIR/robustness-test-results.html || echo 0),
    "failed": $(grep -c "FAILED" $REPORT_DIR/robustness-test-results.html || echo 0)
  }
}
EOF

# Finalize HTML report
cat >> $REPORT_DIR/robustness-test-results.html << EOF
    <h2>Summary</h2>
    <p>Total Tests: 8</p>
    <p>Passed: $(grep -c "PASSED" $REPORT_DIR/robustness-test-results.html || echo 0)</p>
    <p>Failed: $(grep -c "FAILED" $REPORT_DIR/robustness-test-results.html || echo 0)</p>
</body>
</html>
EOF

echo -e "\n${GREEN}Robustness testing complete!${NC}"
echo "Reports generated:"
echo "  - HTML Report: $REPORT_DIR/robustness-test-results.html"
echo "  - Metrics JSON: $METRICS_DIR/robustness-metrics.json"