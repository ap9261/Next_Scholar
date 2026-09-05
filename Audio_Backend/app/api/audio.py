import os
import logging
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.crud.audio import create_audio, get_audio
from app.db.crud.analysis import create_analysis_job
from app.schemas.audio import AudioFileCreate
from app.schemas.analysis import AnalysisJobCreate
from app.services.audio_service import AudioService
from app.tools.metadata import extract_audio_metadata, validate_audio_file
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/audio/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    timeline_json: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
):
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{file.filename}")
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)

    is_valid, error = validate_audio_file(file_path)
    if not is_valid:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=error)

    metadata = extract_audio_metadata(file_path)
    db_audio = create_audio(
        db,
        {
            "filename": file.filename,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "duration": metadata.get("duration"),
            "format": metadata.get("format"),
            "sample_rate": metadata.get("sample_rate"),
            "channels": metadata.get("channels"),
        },
    )

    timeline_path = None
    if timeline_json:
        timeline_path = os.path.join(upload_dir, f"timeline_{uuid.uuid4().hex}_{timeline_json.filename}")
        with open(timeline_path, "wb") as buffer:
            shutil.copyfileobj(timeline_json.file, buffer)

    return {
        "audio_id": db_audio.id,
        "filename": db_audio.filename,
        "status": db_audio.status,
        "duration": db_audio.duration,
        "format": db_audio.format,
        "sample_rate": db_audio.sample_rate,
        "channels": db_audio.channels,
        "file_size": db_audio.file_size,
    }


@router.post("/api/audio/analyze")
async def analyze_audio(
    background_tasks: BackgroundTasks,
    audio_id: str,
    db: Session = Depends(get_db),
):
    db_audio = get_audio(db, audio_id)
    if not db_audio:
        raise HTTPException(status_code=404, detail="Audio not found")

    db_job = create_analysis_job(db, AnalysisJobCreate(audio_id=audio_id, status="queued", current_stage="queued", progress=0.0))

    def run_analysis(audio_id: str, file_path: str, original_filename: str, timeline_path: Optional[str]):
        from app.db.session import SessionLocal
        from app.services.audio_service import AudioService
        from app.core.config import settings

        db = SessionLocal()
        try:
            service = AudioService(
                upload_dir=settings.UPLOAD_DIR,
                output_dir=settings.OUTPUT_DIR,
                ollama_model=settings.OLLAMA_MODEL,
                ollama_base_url=settings.OLLAMA_BASE_URL,
            )
            service.process_audio(db, file_path, original_filename, timeline_path)
        except Exception as e:
            logger.error(f"Background analysis failed for {audio_id}: {e}")
        finally:
            db.close()

    background_tasks.add_task(run_analysis, db_audio.id, db_audio.file_path, db_audio.filename, None)

    return {
        "job_id": db_job.id,
        "status": "queued",
    }
