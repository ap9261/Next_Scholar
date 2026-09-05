from sqlalchemy.orm import Session
from app.db.models import AudioFile
from datetime import datetime
import uuid


def _get(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def create_audio(db: Session, audio) -> AudioFile:
    db_audio = AudioFile(
        id=str(uuid.uuid4()),
        filename=_get(audio, "filename"),
        file_path=_get(audio, "file_path"),
        file_size=_get(audio, "file_size"),
        duration=_get(audio, "duration"),
        format=_get(audio, "format"),
        sample_rate=_get(audio, "sample_rate"),
        channels=_get(audio, "channels"),
        status="uploaded",
    )
    db.add(db_audio)
    db.commit()
    db.refresh(db_audio)
    return db_audio


def get_audio(db: Session, audio_id: str) -> AudioFile | None:
    return db.query(AudioFile).filter(AudioFile.id == audio_id).first()


def get_audio_by_filename(db: Session, filename: str) -> AudioFile | None:
    return db.query(AudioFile).filter(AudioFile.filename == filename).first()


def get_audios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(AudioFile).offset(skip).limit(limit).all()


def update_audio(db: Session, audio_id: str, audio_update) -> AudioFile | None:
    db_audio = get_audio(db, audio_id)
    if not db_audio:
        return None
    if isinstance(audio_update, dict):
        items = audio_update.items()
    else:
        items = audio_update.model_dump(exclude_unset=True).items() if hasattr(audio_update, "model_dump") else vars(audio_update).items()
    for field, value in items:
        if value is not None and hasattr(db_audio, field):
            setattr(db_audio, field, value)
    db_audio.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_audio)
    return db_audio


def delete_audio(db: Session, audio_id: str) -> bool:
    db_audio = get_audio(db, audio_id)
    if not db_audio:
        return False
    db.delete(db_audio)
    db.commit()
    return True
