from fastapi import FastAPI
from routers import model_router

app = FastAPI()

app.include_router(model_router.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
