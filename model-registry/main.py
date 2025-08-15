from fastapi import FastAPI
from routers import model_router, metadata_router
from models.metadata import ModelMetadata

app = FastAPI()

app.include_router(model_router.router, prefix="/api")
app.include_router(metadata_router.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
