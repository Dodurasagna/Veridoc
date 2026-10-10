import logging

from fastapi import FastAPI

from app.api.certificates import router as certificates_router
from app.api.jobs import router as jobs_router
from app.database import Base, engine
from app import models  # noqa: F401 - register SQLAlchemy models before create_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Veridoc", description="Bulk certificate generation and verification API", version="1.0.0")
app.include_router(jobs_router)
app.include_router(certificates_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
