from sqlalchemy import Column, String, Enum, Integer
from database import Base
import enum

class JobStatus(enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"

class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(String, primary_key=True, index=True)
    model_name = Column(String, index=True)
    dataset_location = Column(String)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    cpu_request = Column(Integer, default=1)
