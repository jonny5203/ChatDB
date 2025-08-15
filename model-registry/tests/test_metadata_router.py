import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from database import SessionLocal, engine
from models.metadata import Base, ModelMetadata
from routers.metadata_router import get_db
from sqlalchemy.orm import sessionmaker

@pytest.mark.asyncio
async def test_create_metadata(client):
    response = await client.post("/api/metadata", json={
        "model_name": "test_model",
        "version": "1.0",
        "parameters": {"param1": "value1"},
        "performance_metrics": {"accuracy": 0.9}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "test_model"
    assert data["id"] is not None

@pytest.mark.asyncio
async def test_get_metadata(client):
    response = await client.post("/api/metadata", json={
        "model_name": "test_model",
        "version": "1.0",
        "parameters": {"param1": "value1"},
        "performance_metrics": {"accuracy": 0.9}
    })
    metadata_id = response.json()["id"]
    response = await client.get(f"/api/metadata/{metadata_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == metadata_id
