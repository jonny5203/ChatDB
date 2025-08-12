from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from services.s3_service import S3Service
import os
import tempfile

router = APIRouter()

def get_s3_service():
    return S3Service(
        region_name=os.environ.get("AWS_REGION"),
        bucket_name=os.environ.get("S3_BUCKET_NAME")
    )

@router.post("/models")
def upload_model(file: UploadFile = File(...), s3_service: S3Service = Depends(get_s3_service)):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    s3_service.upload_file(tmp_path, file.filename)
    os.remove(tmp_path)
    return {"filename": file.filename}

@router.get("/models/{model_id}")
def download_model(model_id: str, s3_service: S3Service = Depends(get_s3_service)):
    local_path = f"/tmp/{model_id}"
    s3_service.download_file(model_id, local_path)
    return FileResponse(local_path)