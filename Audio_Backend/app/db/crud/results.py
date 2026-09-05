from sqlalchemy.orm import Session
from app.db.models import AnalysisResult


def get_analysis_summary(db: Session, audio_id: str) -> dict | None:
    results = db.query(AnalysisResult).filter(AnalysisResult.audio_id == audio_id).all()
    if not results:
        return None
    summary = {}
    for r in results:
        summary[r.analysis_type] = {
            "id": r.id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        if r.result_data:
            summary[r.analysis_type]["data"] = r.result_data
        if r.report_text:
            summary[r.analysis_type]["report"] = r.report_text
    return summary


def get_full_result(db: Session, audio_id: str) -> dict | None:
    from app.db.crud.audio import get_audio
    from app.db.crud.transcript import get_transcript_by_audio

    audio = get_audio(db, audio_id)
    if not audio:
        return None

    transcript = get_transcript_by_audio(db, audio_id)
    analysis = get_analysis_summary(db, audio_id)

    result = {
        "job_id": audio_id,
        "status": audio.status,
        "audio": {
            "filename": audio.filename,
            "duration": audio.duration,
            "format": audio.format,
            "sample_rate": audio.sample_rate,
            "channels": audio.channels,
            "file_size": audio.file_size,
        },
        "transcript": None,
        "analysis": analysis or {},
    }

    if transcript:
        result["transcript"] = {
            "text": transcript.text,
            "segments": transcript.segments or [],
            "language": transcript.language,
            "model_used": transcript.model_used,
            "duration": transcript.duration,
        }

    return result
