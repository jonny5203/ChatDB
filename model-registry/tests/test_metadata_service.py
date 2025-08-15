import pytest
from services.metadata_service import MetadataService

def test_create_metadata(metadata_service):
    metadata = metadata_service.create_metadata(
        model_name="test_model",
        version="1.0",
        parameters={"param1": "value1"},
        performance_metrics={"accuracy": 0.9}
    )
    assert metadata.id is not None
    assert metadata.model_name == "test_model"

def test_get_metadata(metadata_service):
    metadata = metadata_service.create_metadata(
        model_name="test_model",
        version="1.0",
        parameters={"param1": "value1"},
        performance_metrics={"accuracy": 0.9}
    )
    retrieved_metadata = metadata_service.get_metadata(metadata.id)
    assert retrieved_metadata.id == metadata.id

def test_update_metadata(metadata_service):
    metadata = metadata_service.create_metadata(
        model_name="test_model",
        version="1.0",
        parameters={"param1": "value1"},
        performance_metrics={"accuracy": 0.9}
    )
    updated_metadata = metadata_service.update_metadata(metadata.id, model_name="updated_model")
    assert updated_metadata.model_name == "updated_model"

def test_delete_metadata(metadata_service):
    metadata = metadata_service.create_metadata(
        model_name="test_model",
        version="1.0",
        parameters={"param1": "value1"},
        performance_metrics={"accuracy": 0.9}
    )
    metadata_service.delete_metadata(metadata.id)
    retrieved_metadata = metadata_service.get_metadata(metadata.id)
    assert retrieved_metadata is None
