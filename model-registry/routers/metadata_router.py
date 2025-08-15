from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.metadata_service import MetadataService
from database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MetadataIn(BaseModel):
    model_name: str
    version: str
    parameters: dict
    performance_metrics: dict

class MetadataOut(MetadataIn):
    id: int

@router.post("/metadata", response_model=MetadataOut)
def create_metadata(metadata: MetadataIn, db: Session = Depends(get_db)):
    service = MetadataService(db)
    return service.create_metadata(**metadata.model_dump())

@router.get("/metadata/{metadata_id}", response_model=MetadataOut)
def get_metadata(metadata_id: int, db: Session = Depends(get_db)):
    service = MetadataService(db)
    metadata = service.get_metadata(metadata_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return metadata

@router.put("/metadata/{metadata_id}", response_model=MetadataOut)
def update_metadata(metadata_id: int, metadata: MetadataIn, db: Session = Depends(get_db)):
    service = MetadataService(db)
    return service.update_metadata(metadata_id, **metadata.model_dump())

@router.delete("/metadata/{metadata_id}")
def delete_metadata(metadata_id: int, db: Session = Depends(get_db)):
    service = MetadataService(db)
    service.delete_metadata(metadata_id)
    return {"status": "ok"}
