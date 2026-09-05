import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
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

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "Audio_Frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="frontend-static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return HTMLResponse(content=index.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)
else:
    @app.get("/", include_in_schema=False)
    async def frontend_missing():
        return HTMLResponse(content="<h1>Frontend not available</h1>", status_code=404)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized")
