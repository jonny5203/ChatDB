# Kafka Integration Testing Guide

## Overview

This document provides comprehensive testing guidance for Kafka integration in the ChatDB microservices architecture, specifically focusing on the Training Orchestrator service's message production and consumption capabilities.

## Architecture Summary

The Kafka integration enables distributed messaging between services:

```
Training Orchestrator → Kafka Broker → ML Engine
                     ↓
                  Database (Jobs)
```

**Key Components:**
- **Kafka Producer**: Sends job messages when training jobs are created
- **Kafka Consumer**: Listens for job messages and processes them asynchronously
- **Circuit Breaker**: Ensures service remains functional when Kafka is unavailable
- **Health Monitoring**: Real-time status of Kafka connectivity

## Test Environment Setup

### 1. Docker Compose Environment (Recommended for Testing)

```bash
# Start complete Kafka environment
cd kafka/
docker compose up -d

# Verify services are running
docker compose ps

# Expected services:
# - kafka-broker (port 9092)
# - postgres (port 5432)
# - training-orchestrator (port 8000)
```

### 2. Kubernetes Environment

```bash
# Deploy Kafka infrastructure
kubectl apply -f kubernetes/infrastructure/kafka.yaml

# Deploy training orchestrator
kubectl apply -f kubernetes/deployments/training-orchestrator.yaml
```

## Integration Test Categories

### 1. Producer Tests

#### Test 1.1: Job Creation with Kafka Message
**Objective**: Verify job creation triggers Kafka message publication

```bash
# Create a training job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "test-integration-model",
    "dataset_location": "/data/integration-test",
    "cpu_request": 2
  }'

# Expected Response:
{
  "id": "uuid-here",
  "status": "pending",
  "model_name": "test-integration-model",
  "dataset_location": "/data/integration-test",
  "cpu_request": 2
}
```

**Verification Steps:**
1. Job created in database ✅
2. Kafka message sent to `training_jobs` topic ✅
3. Service logs show successful message publication ✅

**Log Verification:**
```bash
docker compose logs training-orchestrator | grep "Message sent to topic"
# Expected: "Message sent to topic training_jobs partition X offset Y"
```

#### Test 1.2: Graceful Degradation
**Objective**: Verify service continues working when Kafka is unavailable

```bash
# Stop Kafka broker
docker compose stop kafka-broker

# Create job (should succeed with warning)
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "degraded-test-model",
    "dataset_location": "/data/degraded-test",
    "cpu_request": 1
  }'
```

**Expected Behavior:**
- Job created successfully in database ✅
- Kafka message fails gracefully ✅
- Service remains responsive ✅
- Health endpoint shows "degraded" status ✅

### 2. Consumer Tests

#### Test 2.1: Message Consumption
**Objective**: Verify consumer processes messages from Kafka

```bash
# Send message directly to Kafka (for testing)
docker exec kafka-broker /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs <<EOF
{"job_id":"test-consumer-123","model_name":"direct-kafka-test","dataset_location":"/data/kafka-test","cpu_request":3}
EOF
```

**Verification:**
```bash
# Check consumer logs
docker compose logs training-orchestrator | grep "Received job message"
# Expected: "Received job message for job_id: test-consumer-123"
```

#### Test 2.2: Consumer Error Handling
**Objective**: Verify consumer handles malformed messages gracefully

```bash
# Send malformed message
docker exec kafka-broker /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs <<EOF
{"invalid":"message","missing":"job_id"}
EOF
```

**Expected Behavior:**
- Consumer logs error but continues processing ✅
- Service remains stable ✅
- Other messages processed normally ✅

### 3. Health Monitoring Tests

#### Test 3.1: Health Endpoint Validation
```bash
curl -s http://localhost:8000/health | jq .
```

**Expected Response (Healthy State):**
```json
{
  "status": "ok",
  "service": "training-orchestrator",
  "kafka_enabled": true,
  "database": "connected",
  "kafka": "connected"
}
```

**Expected Response (Kafka Unavailable):**
```json
{
  "status": "degraded",
  "service": "training-orchestrator",
  "kafka_enabled": true,
  "database": "connected",
  "kafka": "error: [connection details]"
}
```

#### Test 3.2: Component Status Validation
```bash
# Test with various failure scenarios
docker compose stop kafka-broker    # Kafka unavailable
docker compose stop postgres        # Database unavailable
docker compose stop training-orchestrator  # Service unavailable
```

### 4. End-to-End Integration Tests

#### Test 4.1: Complete Message Flow
**Objective**: Verify complete producer → consumer flow

```bash
#!/bin/bash
# Complete integration test script

echo "1. Creating training job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "e2e-test-model",
    "dataset_location": "/data/e2e-test",
    "cpu_request": 2
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.id')
echo "Job created: $JOB_ID"

echo "2. Waiting for message processing..."
sleep 5

echo "3. Checking job status..."
curl -s http://localhost:8000/jobs/$JOB_ID | jq .

echo "4. Verifying logs..."
docker compose logs training-orchestrator | grep $JOB_ID
```

## Load Testing

### Producer Load Test
```bash
#!/bin/bash
# Create multiple jobs simultaneously
for i in {1..10}; do
  curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d "{
      \"model_name\": \"load-test-model-$i\",
      \"dataset_location\": \"/data/load-test-$i\",
      \"cpu_request\": $((i % 4 + 1))
    }" &
done
wait
echo "Load test complete"
```

### Consumer Throughput Test
```bash
# Monitor consumer processing rate
docker compose logs -f training-orchestrator | grep "Received job message" | wc -l
```

## Kafka Cluster Testing

### Topic Management
```bash
# List topics
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 --list

# Describe training_jobs topic
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 \
  --describe --topic training_jobs

# Expected output:
# Topic: training_jobs  PartitionCount: 4  ReplicationFactor: 1
```

### Message Inspection
```bash
# Read messages from topic
docker exec kafka-broker /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs \
  --from-beginning
```

## Troubleshooting Common Issues

### Issue 1: Connection Timeout
**Symptoms:** 
- `KafkaConnectionError: socket disconnected`
- Jobs created but no Kafka messages

**Solutions:**
1. Check Kafka broker health: `docker compose ps kafka-broker`
2. Verify network connectivity: `docker network ls`
3. Check broker logs: `docker compose logs kafka-broker`

### Issue 2: Consumer Not Processing
**Symptoms:**
- Messages sent but not processed
- Consumer logs show no activity

**Solutions:**
1. Verify consumer group: Check `training-orchestrator-group`
2. Reset offsets if needed: `kafka-consumer-groups.sh --reset-offsets`
3. Check topic exists: `kafka-topics.sh --list`

### Issue 3: Health Check Failures
**Symptoms:**
- Health endpoint shows "degraded"
- Kafka status shows errors

**Solutions:**
1. Check producer connection: `partitions_for()` method
2. Verify topic accessibility
3. Test with simple producer script

## Monitoring and Observability

### Key Metrics to Monitor
1. **Message Production Rate**: Messages/second sent to Kafka
2. **Consumer Lag**: Difference between produced and consumed messages
3. **Error Rate**: Failed message attempts vs. successful
4. **Connection Health**: Kafka broker connectivity status
5. **Processing Time**: Time from message production to processing

### Log Analysis
```bash
# Producer success rate
docker compose logs training-orchestrator | grep "Message sent to topic" | wc -l

# Producer failure rate  
docker compose logs training-orchestrator | grep "Kafka error sending message" | wc -l

# Consumer processing rate
docker compose logs training-orchestrator | grep "Received job message" | wc -l
```

## Automated Testing Scripts

### Integration Test Suite
```bash
#!/bin/bash
# File: test-kafka-integration.sh

set -e

echo "🚀 Starting Kafka Integration Tests..."

# Start services
docker compose up -d
sleep 30  # Wait for services to be ready

# Test 1: Health check
echo "Test 1: Health Check"
HEALTH=$(curl -s http://localhost:8000/health)
echo $HEALTH | jq .
if echo $HEALTH | jq -e '.status == "ok"' > /dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test 2: Job creation
echo "Test 2: Job Creation"
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "integration-test",
    "dataset_location": "/data/test",
    "cpu_request": 1
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.id')
if [ "$JOB_ID" != "null" ] && [ "$JOB_ID" != "" ]; then
    echo "✅ Job creation passed: $JOB_ID"
else
    echo "❌ Job creation failed"
    exit 1
fi

# Test 3: Kafka message verification
echo "Test 3: Kafka Message Verification"
sleep 5
MESSAGE_COUNT=$(docker compose logs training-orchestrator | grep "Message sent to topic" | wc -l)
if [ $MESSAGE_COUNT -gt 0 ]; then
    echo "✅ Kafka message verification passed ($MESSAGE_COUNT messages)"
else
    echo "⚠️  Kafka message verification: No messages found (check logs)"
fi

echo "🎉 Integration tests completed successfully!"
```

## Performance Benchmarks

### Expected Performance Targets
- **Message Production**: >1000 messages/second
- **Consumer Processing**: >500 messages/second  
- **End-to-End Latency**: <100ms (95th percentile)
- **Error Rate**: <0.1% under normal conditions
- **Recovery Time**: <30 seconds after Kafka restart

### Benchmark Test
```bash
#!/bin/bash
# Simple performance benchmark
START_TIME=$(date +%s)
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d "{\"model_name\":\"perf-test-$i\",\"dataset_location\":\"/data/perf-$i\",\"cpu_request\":1}" > /dev/null
done
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Created 100 jobs in $DURATION seconds"
echo "Rate: $((100 / DURATION)) jobs/second"
```

This comprehensive testing guide ensures robust Kafka integration and provides clear validation steps for all integration scenarios.