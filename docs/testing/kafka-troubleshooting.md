# Kafka Integration Troubleshooting Guide

## 🔍 Diagnostic Commands

### Quick Health Assessment
```bash
# 1. Check all services status
docker compose ps

# 2. Quick health check
curl -s http://localhost:8000/health | jq .

# 3. Check recent logs
docker compose logs --tail=20 training-orchestrator

# 4. Check Kafka broker
docker compose logs --tail=10 kafka-broker
```

## 🚨 Common Issues & Solutions

### Issue 1: `KafkaConnectionError: socket disconnected`

**Symptoms:**
- Jobs created but Kafka messages fail
- Health endpoint shows Kafka error
- Logs show socket disconnection errors

**Root Causes & Solutions:**

#### Cause A: Kafka Broker Not Ready
```bash
# Check if Kafka is fully started
docker compose logs kafka-broker | tail -20

# Wait for broker to be ready
docker compose logs kafka-broker | grep "started (kafka.server.KafkaServer)"

# Solution: Wait longer or restart
docker compose restart kafka-broker
sleep 30  # Wait for full startup
```

#### Cause B: Network Issues
```bash
# Check network connectivity
docker network ls
docker network inspect kafka_default

# Test connectivity from orchestrator to Kafka
docker exec training-orchestrator ping kafka-broker

# Solution: Recreate network
docker compose down
docker compose up -d
```

#### Cause C: Topic Not Found
```bash
# Check if topics exist
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 --list

# Expected: training_jobs, queries, predictions

# Solution: Recreate topics
docker compose up kafka-setup
```

### Issue 2: Consumer Not Processing Messages

**Symptoms:**
- Messages sent to Kafka successfully
- Consumer logs show no message processing
- Jobs remain in "pending" status

**Diagnostic Steps:**
```bash
# 1. Check consumer group status
docker exec kafka-broker /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka-broker:9092 \
  --describe --group training-orchestrator-group

# 2. Check topic has messages
docker exec kafka-broker /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs \
  --from-beginning --timeout-ms 5000

# 3. Check consumer thread is running
docker compose logs training-orchestrator | grep "Kafka Consumer started"
```

**Solutions:**

#### Solution A: Reset Consumer Group
```bash
# Stop service
docker compose stop training-orchestrator

# Reset consumer group offsets
docker exec kafka-broker /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka-broker:9092 \
  --reset-offsets --to-earliest \
  --execute --group training-orchestrator-group \
  --topic training_jobs

# Restart service
docker compose start training-orchestrator
```

#### Solution B: Consumer Thread Issue
```bash
# Check if consumer thread crashed
docker compose logs training-orchestrator | grep "consumer thread ending"

# If found, restart the service
docker compose restart training-orchestrator
```

### Issue 3: Health Endpoint Shows "degraded"

**Symptoms:**
- `/health` returns `"status": "degraded"`
- Service appears to work but health check fails

**Diagnostic Steps:**
```bash
# 1. Check individual component status
curl -s http://localhost:8000/health | jq '{"db": .database, "kafka": .kafka}'

# 2. Test database connection manually
docker exec training-orchestrator python -c "
from database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    result = db.execute(text('SELECT 1'))
    print('DB OK:', result.fetchone())
except Exception as e:
    print('DB Error:', e)
finally:
    db.close()
"

# 3. Test Kafka producer manually
docker exec training-orchestrator python -c "
from kafka import KafkaProducer
import json
try:
    producer = KafkaProducer(
        bootstrap_servers='kafka-broker:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    metadata = producer.partitions_for('training_jobs')
    print('Kafka OK:', metadata)
    producer.close()
except Exception as e:
    print('Kafka Error:', e)
"
```

**Solutions:**

#### Database Issues
```bash
# Check PostgreSQL status
docker compose ps postgres
docker compose logs postgres

# Restart if needed
docker compose restart postgres
```

#### Kafka Partitions Issue
```bash
# Check topic partitions
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 \
  --describe --topic training_jobs

# Recreate topic if needed
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 \
  --delete --topic training_jobs

docker compose up kafka-setup
```

### Issue 4: Service Won't Start

**Symptoms:**
- Container exits immediately
- Import errors in logs
- Database connection failures

**Diagnostic Steps:**
```bash
# 1. Check container status
docker compose ps training-orchestrator

# 2. Check startup logs
docker compose logs training-orchestrator

# 3. Check if it's a build issue
docker compose build training-orchestrator --no-cache
```

**Common Solutions:**

#### Missing Dependencies
```bash
# Check requirements.txt
cat training-orchestrator/requirements.txt

# Rebuild with fresh cache
docker compose build training-orchestrator --no-cache
docker compose up -d training-orchestrator
```

#### Database Not Ready
```bash
# Ensure proper startup order
docker compose down
docker compose up -d postgres
sleep 10  # Wait for DB
docker compose up -d kafka-broker
sleep 20  # Wait for Kafka
docker compose up -d training-orchestrator
```

### Issue 5: High Error Rate

**Symptoms:**
- Many Kafka connection errors in logs
- Messages failing to send
- Consumer reconnecting frequently

**Analysis Commands:**
```bash
# Count error types
docker compose logs training-orchestrator | grep -i error | sort | uniq -c

# Check connection pattern
docker compose logs training-orchestrator | grep "connecting to kafka" | wc -l
docker compose logs training-orchestrator | grep "Connection complete" | wc -l

# Monitor real-time errors
docker compose logs -f training-orchestrator | grep -i error
```

**Performance Solutions:**

#### Increase Connection Timeout
Edit `training-orchestrator/main.py`:
```python
kafka_producer = KafkaProducer(
    bootstrap_servers=kafka_bootstrap_servers,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    retries=5,  # Increase retries
    retry_backoff_ms=2000,  # Increase backoff
    request_timeout_ms=60000,  # Increase timeout
    api_version=(0, 10, 1)
)
```

#### Optimize Consumer Settings
```python
consumer = KafkaConsumer(
    TRAINING_JOBS_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='training-orchestrator-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    session_timeout_ms=30000,  # Increase session timeout
    heartbeat_interval_ms=10000,  # Increase heartbeat
    api_version=(0, 10, 1)
)
```

## 🧪 Verification Tests

### Test 1: End-to-End Message Flow
```bash
#!/bin/bash
echo "Testing complete message flow..."

# Create job and capture ID
RESPONSE=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"e2e-test","dataset_location":"/data/e2e","cpu_request":1}')

JOB_ID=$(echo $RESPONSE | jq -r '.id')
echo "Created job: $JOB_ID"

# Wait and check for Kafka message
sleep 3
MESSAGE_FOUND=$(docker compose logs training-orchestrator | grep "Message sent.*$JOB_ID" | wc -l)

if [ $MESSAGE_FOUND -gt 0 ]; then
    echo "✅ Message flow working"
else
    echo "❌ Message flow broken"
    echo "Debug: Check producer logs"
    docker compose logs training-orchestrator | tail -10
fi
```

### Test 2: Consumer Processing
```bash
#!/bin/bash
echo "Testing consumer processing..."

# Send direct message to Kafka
docker exec kafka-broker /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs <<EOF
{"job_id":"consumer-test-123","model_name":"consumer-test","dataset_location":"/data/consumer-test","cpu_request":2}
EOF

# Wait and check for processing
sleep 5
PROCESSED=$(docker compose logs training-orchestrator | grep "consumer-test-123" | wc -l)

if [ $PROCESSED -gt 0 ]; then
    echo "✅ Consumer processing working"
else
    echo "❌ Consumer processing broken"
    echo "Debug: Check consumer logs"
    docker compose logs training-orchestrator | grep "Received job message" | tail -5
fi
```

### Test 3: Resilience Test
```bash
#!/bin/bash
echo "Testing system resilience..."

# Test with Kafka down
docker compose stop kafka-broker

RESPONSE=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"resilience-test","dataset_location":"/data/resilience","cpu_request":1}')

if echo $RESPONSE | jq -e '.id' > /dev/null; then
    echo "✅ Resilience test passed - service works without Kafka"
else
    echo "❌ Resilience test failed"
fi

# Restart Kafka
docker compose start kafka-broker
echo "Kafka restarted"
```

## 📊 Performance Monitoring

### Real-time Monitoring Commands
```bash
# Monitor message throughput
watch 'docker compose logs training-orchestrator | grep "Message sent" | wc -l'

# Monitor error rate
watch 'docker compose logs training-orchestrator | grep -i error | wc -l'

# Monitor connection health
watch 'curl -s http://localhost:8000/health | jq -r ".kafka"'
```

### Log Analysis for Performance
```bash
# Get message sending rate (messages per minute)
docker compose logs training-orchestrator | \
grep "Message sent" | \
awk '{print $1" "$2}' | \
sort | uniq -c | \
tail -10

# Get error frequency
docker compose logs training-orchestrator | \
grep -i error | \
awk '{print $1" "$2}' | \
sort | uniq -c | \
tail -10
```

## 🛠 Recovery Procedures

### Complete System Reset
```bash
#!/bin/bash
echo "Performing complete system reset..."

# 1. Stop everything
docker compose down -v

# 2. Clean up
docker system prune -f
docker volume prune -f

# 3. Rebuild
docker compose build --no-cache

# 4. Start infrastructure first
docker compose up -d postgres kafka-broker

# 5. Wait for readiness
sleep 30

# 6. Start application
docker compose up -d training-orchestrator

# 7. Verify
sleep 10
curl -s http://localhost:8000/health | jq .
```

### Partial Recovery (Keep Data)
```bash
#!/bin/bash
echo "Performing partial recovery..."

# 1. Stop application only
docker compose stop training-orchestrator

# 2. Rebuild application
docker compose build training-orchestrator

# 3. Restart application
docker compose up -d training-orchestrator

# 4. Verify
sleep 5
curl -s http://localhost:8000/health | jq .
```

## 📞 Getting Help

When reporting issues, include:

1. **Environment Info:**
   ```bash
   docker --version
   docker compose version
   uname -a
   ```

2. **Service Status:**
   ```bash
   docker compose ps
   ```

3. **Recent Logs:**
   ```bash
   docker compose logs --tail=50 training-orchestrator
   docker compose logs --tail=20 kafka-broker
   ```

4. **Health Status:**
   ```bash
   curl -s http://localhost:8000/health | jq .
   ```

5. **Error Details:**
   ```bash
   docker compose logs training-orchestrator | grep -i error | tail -10
   ```

This information helps quickly identify and resolve Kafka integration issues.