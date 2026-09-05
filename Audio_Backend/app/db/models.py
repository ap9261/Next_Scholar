from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Float)
    duration = Column(Float)
    format = Column(String)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    status = Column(String, default="uploaded")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transcripts = relationship("Transcript", back_populates="audio", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="audio", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, index=True)
    audio_id = Column(String, ForeignKey("audio_files.id"), nullable=False)
    text = Column(Text)
    segments = Column(JSON)
    language = Column(String, nullable=True)
    model_used = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    audio = relationship("AudioFile", back_populates="transcripts")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String, primary_key=True, index=True)
    transcript_id = Column(String, ForeignKey("transcripts.id"), nullable=False)
    start = Column(Float, nullable=False)
    end = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    speaker = Column(String, nullable=True)
    segment_index = Column(Integer, nullable=False)


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(String, primary_key=True, index=True)
    audio_id = Column(String, ForeignKey("audio_files.id"), nullable=False)
    name = Column(String, nullable=False)
    is_teacher = Column(Boolean, default=False)
    segment_count = Column(Integer, default=0)
    total_duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, index=True)
    audio_id = Column(String, ForeignKey("audio_files.id"), nullable=False)
    analysis_type = Column(String, nullable=False)
    result_data = Column(JSON)
    report_text = Column(Text, nullable=True)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audio = relationship("AudioFile", back_populates="analysis_results")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String, primary_key=True, index=True)
    audio_id = Column(String, ForeignKey("audio_files.id"), nullable=False)
    status = Column(String, default="queued")
    current_stage = Column(String, nullable=True)
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
