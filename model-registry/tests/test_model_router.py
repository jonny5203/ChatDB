import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from moto import mock_aws
import boto3
import os

@pytest.fixture(scope="function")
async def client():
    with mock_aws():
        os.environ["AWS_REGION"] = "us-east-1"
        os.environ["S3_BUCKET_NAME"] = "test-bucket"
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

@pytest.mark.asyncio
async def test_upload_model(client):
    with open("test_model.bin", "wb") as f:
        f.write(b"test model content")
    with open("test_model.bin", "rb") as f:
        response = await client.post("/api/models", files={"file": f})
    assert response.status_code == 200
    assert response.json() == {"filename": "test_model.bin"}

@pytest.mark.asyncio
async def test_download_model(client):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="test-bucket", Key="test_model.bin", Body=b"test model content")
    response = await client.get("/api/models/test_model.bin")
    assert response.status_code == 200
    assert response.content == b"test model content"
