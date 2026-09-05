from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any


class TranscriptBase(BaseModel):
    audio_id: str
    text: Optional[str] = None
    segments: Optional[Any] = None
    language: Optional[str] = None
    model_used: Optional[str] = None
    duration: Optional[float] = None


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptResponse(TranscriptBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: Optional[datetime] = None


class TranscriptSegmentCreate(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    segment_index: int


class TranscriptSegmentResponse(TranscriptSegmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transcript_id: str


class SpeakerBase(BaseModel):
    audio_id: str
    name: str
    is_teacher: bool = False
    segment_count: int = 0
    total_duration: float = 0.0


class SpeakerCreate(SpeakerBase):
    pass


class SpeakerResponse(SpeakerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: Optional[datetime] = None


class AnalysisResultBase(BaseModel):
    audio_id: str
    analysis_type: str
    result_data: Optional[Any] = None
    report_text: Optional[str] = None
    status: str = "pending"


class AnalysisResultCreate(AnalysisResultBase):
    pass


class AnalysisResultResponse(AnalysisResultBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AnalysisJobCreate(BaseModel):
    audio_id: str
    status: str = "queued"
    current_stage: Optional[str] = None
    progress: float = 0.0


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    audio_id: str
    status: str
    current_stage: Optional[str] = None
    progress: float
    error_message: Optional[str] = None
    result: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
