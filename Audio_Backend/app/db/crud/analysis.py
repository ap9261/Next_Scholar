from sqlalchemy.orm import Session
from app.db.models import AnalysisResult, AnalysisJob, Speaker
from datetime import datetime
import uuid


def _get(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def create_analysis_result(db: Session, result) -> AnalysisResult:
    db_result = AnalysisResult(
        id=str(uuid.uuid4()),
        audio_id=_get(result, "audio_id"),
        analysis_type=_get(result, "analysis_type"),
        result_data=_get(result, "result_data"),
        report_text=_get(result, "report_text"),
        status=_get(result, "status", "pending"),
        error_message=_get(result, "error_message"),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_analysis_result(db: Session, result_id: str) -> AnalysisResult | None:
    return db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()


def get_analysis_results_by_audio(db: Session, audio_id: str):
    return db.query(AnalysisResult).filter(AnalysisResult.audio_id == audio_id).all()


def get_analysis_result_by_type(db: Session, audio_id: str, analysis_type: str) -> AnalysisResult | None:
    return db.query(AnalysisResult).filter(
        AnalysisResult.audio_id == audio_id,
        AnalysisResult.analysis_type == analysis_type
    ).first()


def create_analysis_job(db: Session, job) -> AnalysisJob:
    db_job = AnalysisJob(
        id=str(uuid.uuid4()),
        audio_id=_get(job, "audio_id"),
        status=_get(job, "status", "queued"),
        current_stage=_get(job, "current_stage"),
        progress=_get(job, "progress", 0.0),
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_analysis_job(db: Session, job_id: str) -> AnalysisJob | None:
    return db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()


def update_analysis_job(db: Session, job_id: str, status: str | None = None, current_stage: str | None = None, progress: float | None = None, result: dict | None = None, error_message: str | None = None) -> AnalysisJob | None:
    db_job = get_analysis_job(db, job_id)
    if not db_job:
        return None
    if status is not None:
        db_job.status = status
    if current_stage is not None:
        db_job.current_stage = current_stage
    if progress is not None:
        db_job.progress = progress
    if result is not None:
        db_job.result = result
    if error_message is not None:
        db_job.error_message = error_message
    db_job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_job)
    return db_job


def create_speaker(db: Session, speaker) -> Speaker:
    db_speaker = Speaker(
        id=str(uuid.uuid4()),
        audio_id=_get(speaker, "audio_id"),
        name=_get(speaker, "name"),
        is_teacher=_get(speaker, "is_teacher", False),
        segment_count=_get(speaker, "segment_count", 0),
        total_duration=_get(speaker, "total_duration", 0.0),
    )
    db.add(db_speaker)
    db.commit()
    db.refresh(db_speaker)
    return db_speaker


def get_speakers_by_audio(db: Session, audio_id: str):
    return db.query(Speaker).filter(Speaker.audio_id == audio_id).all()
