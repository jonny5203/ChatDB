from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ModelMetadata(Base):
    __tablename__ = 'model_metadata'

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    parameters = Column(JSON)
    performance_metrics = Column(JSON)

    def __repr__(self):
        return f"<ModelMetadata(model_name='{self.model_name}', version='{self.version}')>"
