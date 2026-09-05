from sqlalchemy.orm import Session
from app.db.models import Transcript, TranscriptSegment
from datetime import datetime
import uuid


def _get(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def create_transcript(db: Session, transcript) -> Transcript:
    db_transcript = Transcript(
        id=str(uuid.uuid4()),
        audio_id=_get(transcript, "audio_id"),
        text=_get(transcript, "text"),
        segments=_get(transcript, "segments"),
        language=_get(transcript, "language"),
        model_used=_get(transcript, "model_used"),
        duration=_get(transcript, "duration"),
    )
    db.add(db_transcript)
    db.commit()
    db.refresh(db_transcript)
    return db_transcript


def get_transcript(db: Session, transcript_id: str) -> Transcript | None:
    return db.query(Transcript).filter(Transcript.id == transcript_id).first()


def get_transcript_by_audio(db: Session, audio_id: str) -> Transcript | None:
    return db.query(Transcript).filter(Transcript.audio_id == audio_id).first()


def create_transcript_segment(db: Session, segment, transcript_id: str) -> TranscriptSegment:
    db_segment = TranscriptSegment(
        id=str(uuid.uuid4()),
        transcript_id=transcript_id,
        start=_get(segment, "start", 0),
        end=_get(segment, "end", 0),
        text=_get(segment, "text", ""),
        speaker=_get(segment, "speaker"),
        segment_index=_get(segment, "segment_index", 0),
    )
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment


def get_segments_by_transcript(db: Session, transcript_id: str):
    return db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript_id).order_by(TranscriptSegment.segment_index).all()
