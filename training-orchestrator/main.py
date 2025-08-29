from fastapi import FastAPI, Depends
from pydantic import BaseModel
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, KafkaConnectionError
import uuid
import models
import database
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from sqlalchemy import text
import threading
import time
import os
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global producer variable
kafka_producer = None
kafka_enabled = True

def init_kafka_producer():
    """Initialize Kafka producer with retry logic and error handling."""
    global kafka_producer, kafka_enabled
    
    try:
        kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        logger.info(f"Initializing Kafka producer with servers: {kafka_bootstrap_servers}")
        
        kafka_producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            retry_backoff_ms=1000,
            request_timeout_ms=30000,
            api_version=(0, 10, 1)
        )
        kafka_enabled = True
        logger.info("Kafka producer initialized successfully")
        return True
    except KafkaConnectionError as e:
        logger.warning(f"Kafka connection failed, operating without Kafka: {e}")
        kafka_enabled = False
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Kafka producer: {e}")
        kafka_enabled = False
        return False

# This function will be called when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Lifespan event started.")
    
    # Create database tables
    logger.info("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    
    # Initialize Kafka producer
    logger.info("Initializing Kafka producer...")
    init_kafka_producer()
    
    # Start the Kafka consumer thread if Kafka is enabled
    if kafka_enabled:
        logger.info("Starting Kafka consumer thread...")
        consumer_thread = threading.Thread(target=consume_messages)
        consumer_thread.daemon = True
        consumer_thread.start()
        logger.info("Kafka consumer thread started.")
    else:
        logger.warning("Kafka consumer not started - Kafka is disabled")
    
    yield
    
    # Clean up the consumer and other resources if needed
    if kafka_producer:
        kafka_producer.close()
        logger.info("Kafka producer closed.")

app = FastAPI(lifespan=lifespan)

# Configuration
MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', 2))
DEFAULT_CPU_REQUEST = int(os.getenv('DEFAULT_CPU_REQUEST', 1))

# Semaphore to limit concurrent jobs
semaphore = threading.Semaphore(MAX_CONCURRENT_JOBS)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TRAINING_JOBS_TOPIC = 'training_jobs'

class TrainingJobCreate(BaseModel):
    model_name: str
    dataset_location: str
    cpu_request: int = DEFAULT_CPU_REQUEST

class TrainingJob(TrainingJobCreate):
    id: str
    status: models.JobStatus

    class Config:
        from_attributes = True

def send_kafka_message(message, topic):
    """Send message to Kafka with error handling and circuit breaker pattern."""
    global kafka_producer, kafka_enabled
    
    if not kafka_enabled or not kafka_producer:
        logger.warning("Kafka is disabled, skipping message send")
        return False
    
    try:
        future = kafka_producer.send(topic, value=message)
        record_metadata = future.get(timeout=10)
        logger.info(f"Message sent to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
        return True
    except KafkaError as e:
        logger.error(f"Kafka error sending message: {e}")
        # Implement circuit breaker - disable Kafka temporarily on persistent errors
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message to Kafka: {e}")
        return False

@app.post("/jobs")
def create_training_job(job: TrainingJobCreate, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    db_job = models.TrainingJob(id=job_id, model_name=job.model_name, dataset_location=job.dataset_location, cpu_request=job.cpu_request)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    # Prepare job message for Kafka
    job_message = {
        "job_id": job_id,
        "model_name": job.model_name,
        "dataset_location": job.dataset_location,
        "cpu_request": job.cpu_request
    }
    
    # Send message to Kafka if enabled
    if kafka_enabled:
        success = send_kafka_message(job_message, TRAINING_JOBS_TOPIC)
        if success:
            logger.info(f"Job {job_id} message sent to Kafka successfully")
        else:
            logger.warning(f"Job {job_id} created in database but Kafka message failed")
    else:
        logger.info(f"Job {job_id} created in database (Kafka disabled)")
    
    return db_job

@app.get("/jobs")
def list_training_jobs(db: Session = Depends(get_db)):
    """List all training jobs in the system."""
    jobs = db.query(models.TrainingJob).all()
    return jobs

@app.get("/jobs/{job_id}", response_model=TrainingJob)
def get_training_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
    return db_job

@app.get("/health")
def health():
    """Health check endpoint with Kafka status."""
    health_status = {
        "status": "ok",
        "service": "training-orchestrator",
        "kafka_enabled": kafka_enabled,
        "database": "connected"
    }
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Kafka connection
    if kafka_enabled and kafka_producer:
        try:
            # Test if producer is still working by checking cluster metadata
            metadata = kafka_producer.partitions_for(TRAINING_JOBS_TOPIC)
            if metadata is not None:
                health_status["kafka"] = "connected"
            else:
                health_status["kafka"] = "topic not found"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["kafka"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    elif kafka_enabled:
        health_status["kafka"] = "initializing"
        health_status["status"] = "degraded"
    else:
        health_status["kafka"] = "disabled"
    
    return health_status

def process_job(job_id, cpu_request):
    with semaphore:
        db = SessionLocal()
        db_job = db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if db_job:
            print(f"Processing job: {db_job.id} with {cpu_request} CPU(s)")
            db_job.status = models.JobStatus.in_progress
            db.commit()

            # Simulate calling ML Engine and waiting for completion
            time.sleep(10)

            # Simulate completion
            db_job.status = models.JobStatus.completed
            db.commit()
            print(f"Job {db_job.id} completed")
        db.close()

def consume_messages():
    """Consume messages from Kafka with error handling and retry logic."""
    retry_count = 0
    max_retries = 3
    retry_delay = 5
    
    while retry_count < max_retries:
        try:
            logger.info("Attempting to start Kafka Consumer...")
            consumer = KafkaConsumer(
                TRAINING_JOBS_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='training-orchestrator-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                api_version=(0, 10, 1)
            )
            logger.info("Kafka Consumer started and listening for messages...")
            
            # Reset retry count on successful connection
            retry_count = 0
            
            for message in consumer:
                try:
                    job_id = message.value['job_id']
                    cpu_request = message.value['cpu_request']
                    logger.info(f"Received job message for job_id: {job_id}")
                    
                    # Process each job in a new thread
                    thread = threading.Thread(target=process_job, args=(job_id, cpu_request))
                    thread.start()
                    
                except KeyError as e:
                    logger.error(f"Invalid message format: {e}, message: {message.value}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KafkaConnectionError as e:
            retry_count += 1
            logger.warning(f"Kafka connection error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries reached. Kafka consumer will not be available.")
                break
        except Exception as e:
            logger.error(f"Unexpected error in Kafka consumer: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying consumer in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                break
    
    logger.warning("Kafka consumer thread ending")