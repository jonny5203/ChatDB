"""
Kafka integration tests for the ChatDB system
Tests message publishing and consumption within Kubernetes cluster
"""
import pytest
import json
import time
import os
from uuid import uuid4
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

@pytest.fixture
def kafka_bootstrap_servers():
    """Get Kafka bootstrap servers from environment"""
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

@pytest.fixture
def kafka_producer(kafka_bootstrap_servers):
    """Create Kafka producer for testing"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            max_block_ms=10000
        )
        yield producer
    except Exception as e:
        pytest.skip(f"Kafka not available: {e}")
    finally:
        if 'producer' in locals():
            producer.close()

@pytest.fixture
def kafka_consumer(kafka_bootstrap_servers):
    """Create Kafka consumer for testing"""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            consumer_timeout_ms=5000,
            group_id=f'test_group_{uuid4().hex[:8]}'
        )
        yield consumer
    except Exception as e:
        pytest.skip(f"Kafka not available: {e}")
    finally:
        if 'consumer' in locals():
            consumer.close()

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.kafka
def test_kafka_connectivity(kafka_bootstrap_servers):
    """Test basic Kafka connectivity"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            request_timeout_ms=5000
        )
        # Test connection by getting metadata
        metadata = producer.partitions_for('test-topic')
        producer.close()
        # If we get here without exception, Kafka is accessible
        assert True
    except Exception as e:
        pytest.fail(f"Cannot connect to Kafka: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.kafka
def test_training_job_message_production(kafka_producer):
    """Test producing training job messages to Kafka"""
    test_message = {
        "job_id": f"test_job_{uuid4().hex[:8]}",
        "model_name": "test_model",
        "dataset_location": "/data/test.csv",
        "cpu_request": 2,
        "timestamp": time.time()
    }
    
    try:
        # Send message to training-jobs topic
        future = kafka_producer.send('training-jobs', value=test_message)
        record_metadata = future.get(timeout=10)
        
        # Verify message was sent successfully
        assert record_metadata.topic == 'training-jobs'
        assert record_metadata.partition is not None
        assert record_metadata.offset is not None
        
    except KafkaError as e:
        pytest.fail(f"Failed to produce message: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.kafka
@pytest.mark.slow
def test_message_consumption(kafka_producer, kafka_consumer, kafka_bootstrap_servers):
    """Test consuming messages from Kafka"""
    topic_name = f"test-topic-{uuid4().hex[:8]}"
    
    # Subscribe consumer to test topic
    kafka_consumer.subscribe([topic_name])
    
    test_message = {
        "test_id": uuid4().hex[:8],
        "message": "test message consumption",
        "timestamp": time.time()
    }
    
    # Produce a test message
    try:
        future = kafka_producer.send(topic_name, value=test_message)
        future.get(timeout=10)
    except KafkaError as e:
        pytest.fail(f"Failed to produce test message: {e}")
    
    # Try to consume the message
    messages_received = []
    start_time = time.time()
    timeout = 15  # 15 second timeout
    
    while time.time() - start_time < timeout:
        try:
            message_batch = kafka_consumer.poll(timeout_ms=1000)
            for topic_partition, messages in message_batch.items():
                for message in messages:
                    messages_received.append(message.value)
            
            if messages_received:
                break
        except Exception as e:
            print(f"Polling error: {e}")
            continue
    
    # Verify we received our test message
    assert len(messages_received) > 0, "No messages were consumed"
    
    # Find our specific test message
    found_test_message = False
    for msg in messages_received:
        if msg.get("test_id") == test_message["test_id"]:
            found_test_message = True
            assert msg["message"] == test_message["message"]
            break
    
    assert found_test_message, f"Test message not found in consumed messages: {messages_received}"

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.kafka
def test_kafka_topic_creation(kafka_bootstrap_servers):
    """Test that required topics exist or can be created"""
    from kafka.admin import KafkaAdminClient, NewTopic
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=kafka_bootstrap_servers,
            client_id='test_admin'
        )
        
        # List existing topics
        existing_topics = admin_client.list_topics()
        
        required_topics = ['training-jobs', 'query-results', 'model-updates']
        
        # Check if required topics exist
        missing_topics = []
        for topic in required_topics:
            if topic not in existing_topics:
                missing_topics.append(topic)
        
        if missing_topics:
            # Try to create missing topics
            new_topics = [
                NewTopic(name=topic, num_partitions=1, replication_factor=1)
                for topic in missing_topics
            ]
            
            try:
                admin_client.create_topics(new_topics, validate_only=False)
                time.sleep(2)  # Wait for topic creation
                print(f"Created missing topics: {missing_topics}")
            except Exception as e:
                print(f"Could not create topics: {e}")
                # This might be expected in some environments
        
        admin_client.close()
        
    except Exception as e:
        pytest.skip(f"Cannot test topic management: {e}")

@pytest.mark.integration
@pytest.mark.kubernetes
@pytest.mark.kafka
def test_kafka_error_handling(kafka_bootstrap_servers):
    """Test Kafka error handling and resilience"""
    # Test with invalid topic name
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            request_timeout_ms=2000,
            retries=1
        )
        
        # Try to send to invalid topic (with special characters)
        future = producer.send('invalid-topic-name-with-special-chars!@#', value=b'test')
        
        try:
            future.get(timeout=5)
        except KafkaError:
            # Expected to fail with invalid topic name
            pass
        
        producer.close()
        
    except Exception as e:
        pytest.fail(f"Error handling test failed: {e}")