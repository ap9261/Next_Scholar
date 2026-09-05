import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.audio import router as audio_router
from app.api.analysis import router as analysis_router
from app.core.config import settings
from app.db.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(title="NextScholar Audio Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(audio_router)
app.include_router(analysis_router)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized")
