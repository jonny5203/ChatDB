from sqlalchemy.orm import Session
from models.metadata import ModelMetadata

class MetadataService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_metadata(self, model_name: str, version: str, parameters: dict, performance_metrics: dict) -> ModelMetadata:
        metadata = ModelMetadata(
            model_name=model_name,
            version=version,
            parameters=parameters,
            performance_metrics=performance_metrics
        )
        self.db_session.add(metadata)
        self.db_session.commit()
        self.db_session.refresh(metadata)
        return metadata

    def get_metadata(self, metadata_id: int) -> ModelMetadata:
        return self.db_session.query(ModelMetadata).filter_by(id=metadata_id).first()

    def update_metadata(self, metadata_id: int, **kwargs) -> ModelMetadata:
        metadata = self.get_metadata(metadata_id)
        if metadata:
            for key, value in kwargs.items():
                setattr(metadata, key, value)
            self.db_session.commit()
            self.db_session.refresh(metadata)
        return metadata

    def delete_metadata(self, metadata_id: int):
        metadata = self.get_metadata(metadata_id)
        if metadata:
            self.db_session.delete(metadata)
            self.db_session.commit()
