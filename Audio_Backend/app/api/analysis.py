import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import AnalysisJob, AudioFile
from app.db.crud.results import get_full_result

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/audio/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "audio_id": job.audio_id,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress": job.progress,
        "error_message": job.error_message,
    }


@router.get("/api/audio/result/{job_id}")
async def get_job_result(job_id: str, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = get_full_result(db, job.audio_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.get("/api/audio/{audio_id}")
async def get_audio_info(audio_id: str, db: Session = Depends(get_db)):
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return {
        "id": audio.id,
        "filename": audio.filename,
        "status": audio.status,
        "duration": audio.duration,
        "format": audio.format,
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "file_size": audio.file_size,
        "error_message": audio.error_message,
        "created_at": audio.created_at.isoformat() if audio.created_at else None,
        "updated_at": audio.updated_at.isoformat() if audio.updated_at else None,
    }
