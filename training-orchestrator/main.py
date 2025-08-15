from fastapi import FastAPI, Depends
from pydantic import BaseModel
import json
from kafka import KafkaProducer, KafkaConsumer
import uuid
from . import models, database
from .database import SessionLocal, engine
from sqlalchemy.orm import Session
import threading
import time

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuration
MAX_CONCURRENT_JOBS = 2
DEFAULT_CPU_REQUEST = 1

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
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092' # Replace with your Kafka broker address
TRAINING_JOBS_TOPIC = 'training_jobs'

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

class TrainingJobCreate(BaseModel):
    model_name: str
    dataset_location: str
    cpu_request: int = DEFAULT_CPU_REQUEST

class TrainingJob(TrainingJobCreate):
    id: str
    status: models.JobStatus

    class Config:
        orm_mode = True

@app.post("/jobs", response_model=TrainingJob)
def create_training_job(job: TrainingJobCreate, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    db_job = models.TrainingJob(id=job_id, model_name=job.model_name, dataset_location=job.dataset_location, cpu_request=job.cpu_request)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    job_message = {
        "job_id": job_id,
        "model_name": job.model_name,
        "dataset_location": job.dataset_location,
        "cpu_request": job.cpu_request
    }
    producer.send(TRAINING_JOBS_TOPIC, value=job_message)
    return db_job

@app.get("/jobs/{job_id}", response_model=TrainingJob)
def get_training_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
    return db_job

@app.get("/health")
def health():
    return {"status": "ok"}

# Kafka Consumer (runs in the background)
consumer = KafkaConsumer(
    TRAINING_JOBS_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='training-orchestrator-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

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
    for message in consumer:
        job_id = message.value['job_id']
        cpu_request = message.value['cpu_request']
        # Process each job in a new thread
        thread = threading.Thread(target=process_job, args=(job_id, cpu_request))
        thread.start()

consumer_thread = threading.Thread(target=consume_messages)
consumer_thread.daemon = True
consumer_thread.start()
