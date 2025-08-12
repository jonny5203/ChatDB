import boto3

class S3Service:
    def __init__(self, region_name: str, bucket_name: str):
        self.s3 = boto3.client("s3", region_name=region_name)
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str, object_name: str):
        self.s3.upload_file(file_path, self.bucket_name, object_name)

    def download_file(self, object_name: str, file_path: str):
        self.s3.download_file(self.bucket_name, object_name, file_path)