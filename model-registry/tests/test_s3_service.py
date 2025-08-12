import boto3
import pytest
from moto import mock_aws
from services.s3_service import S3Service

@pytest.fixture
def s3_service():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        yield S3Service(region_name="us-east-1", bucket_name="test-bucket")

def test_upload_file(s3_service):
    with open("test_file.txt", "w") as f:
        f.write("test content")
    s3_service.upload_file("test_file.txt", "test_file.txt")
    response = s3_service.s3.get_object(Bucket="test-bucket", Key="test_file.txt")
    assert response["Body"].read().decode() == "test content"

def test_download_file(s3_service):
    s3_service.s3.put_object(Bucket="test-bucket", Key="test_file.txt", Body="test content")
    s3_service.download_file("test_file.txt", "downloaded_file.txt")
    with open("downloaded_file.txt", "r") as f:
        assert f.read() == "test content"
