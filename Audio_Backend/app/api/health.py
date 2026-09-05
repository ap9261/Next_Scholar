import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.db.database import init_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    from app.core.config import settings
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.OLLAMA_BASE_URL.replace("/api/generate", "/api/tags"), timeout=2.0)
            ollama_status = "running" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unavailable"

    return {
        "status": "ok",
        "ollama_status": ollama_status,
        "database_status": db_status,
    }


@router.post("/health/init-db")
async def init_database():
    init_db()
    return {"status": "database initialized"}
