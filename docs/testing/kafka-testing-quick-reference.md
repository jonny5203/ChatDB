# Kafka Testing Quick Reference

## 🚀 Quick Start

```bash
# 1. Start Kafka environment
cd kafka/ && docker compose up -d

# 2. Wait for services (30 seconds)
sleep 30

# 3. Test health
curl -s http://localhost:8000/health | jq .

# 4. Create test job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"quick-test","dataset_location":"/data/test","cpu_request":1}' | jq .
```

## 🔍 Common Test Commands

### Health Checks
```bash
# Full health status
curl -s http://localhost:8000/health | jq .

# Quick health check
curl -s http://localhost:8000/health | jq -r '.status'
```

### Job Operations
```bash
# Create job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"model_name":"test","dataset_location":"/data","cpu_request":2}' | jq .

# Get job by ID
curl -s http://localhost:8000/jobs/JOB_ID_HERE | jq .
```

### Kafka Message Inspection
```bash
# Read messages from topic
docker exec kafka-broker /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs \
  --from-beginning

# Send test message
echo '{"job_id":"test-123","model_name":"manual","dataset_location":"/test","cpu_request":1}' | \
docker exec -i kafka-broker /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka-broker:9092 \
  --topic training_jobs
```

### Log Analysis
```bash
# Producer logs
docker compose logs training-orchestrator | grep "Message sent"

# Consumer logs  
docker compose logs training-orchestrator | grep "Received job message"

# Error logs
docker compose logs training-orchestrator | grep "error\|Error\|ERROR"

# Kafka connection logs
docker compose logs training-orchestrator | grep "kafka.conn"
```

## 🛠 Troubleshooting Commands

### Service Status
```bash
# Check all services
docker compose ps

# Check specific service
docker compose ps training-orchestrator

# Restart service
docker compose restart training-orchestrator
```

### Kafka Broker Health
```bash
# Check Kafka topics
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 --list

# Check topic details
docker exec kafka-broker /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka-broker:9092 \
  --describe --topic training_jobs
```

### Database Check
```bash
# Connect to database
docker exec -it postgres psql -U user -d db

# Check jobs table
# \dt
# SELECT id, model_name, status FROM training_jobs LIMIT 5;
```

## ⚡ Quick Tests

### Test 1: Basic Functionality
```bash
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"model_name":"test1","dataset_location":"/data/test1","cpu_request":1}' && echo "✅ Job creation works"
```

### Test 2: Graceful Degradation
```bash
docker compose stop kafka-broker
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"model_name":"test2","dataset_location":"/data/test2","cpu_request":1}' && echo "✅ Graceful degradation works"
docker compose start kafka-broker
```

### Test 3: Health Status
```bash
curl -s http://localhost:8000/health | jq -r '.status' | grep -q "ok\|degraded" && echo "✅ Health check works"
```

## 📊 Performance Tests

### Load Test (10 jobs)
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d "{\"model_name\":\"load-$i\",\"dataset_location\":\"/data/load-$i\",\"cpu_request\":$((i%4+1))}" &
done; wait; echo "Load test complete"
```

### Message Rate Test
```bash
# Run for 10 seconds and count messages
timeout 10s docker compose logs -f training-orchestrator | grep "Message sent" | wc -l
```

## 🔧 Environment Variables

### Training Orchestrator
```bash
# Set custom Kafka servers
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Set job limits
export MAX_CONCURRENT_JOBS=5
export DEFAULT_CPU_REQUEST=2
```

### Docker Compose Override
```yaml
# docker-compose.override.yml
services:
  training-orchestrator:
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=custom-kafka:9092
      - MAX_CONCURRENT_JOBS=10
```

## 🚨 Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| `Connection refused` | `docker compose restart kafka-broker` |
| `Topic not found` | `docker compose up kafka-setup` |
| `Database error` | `docker compose restart postgres` |
| `Port in use` | `docker compose down && docker compose up -d` |
| `Health degraded` | Check logs: `docker compose logs training-orchestrator` |

## 📋 Test Checklist

- [ ] Services start successfully
- [ ] Health endpoint returns status
- [ ] Job creation works
- [ ] Database persistence works
- [ ] Kafka messages sent (when available)
- [ ] Graceful degradation works
- [ ] Consumer processes messages
- [ ] Error handling works
- [ ] Service restart works
- [ ] Load testing passes

## 🎯 Success Criteria

✅ **Producer Integration**
- Jobs trigger Kafka messages
- Messages contain correct data
- Error handling works gracefully

✅ **Consumer Integration**  
- Messages processed from Kafka
- Job processing starts correctly
- Invalid messages handled

✅ **System Resilience**
- Service works without Kafka
- Automatic reconnection works
- Health monitoring accurate

✅ **Performance**
- >100 jobs/minute creation rate
- <100ms message latency
- <1% error rate under load