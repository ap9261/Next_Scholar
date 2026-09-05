from pydantic import BaseModel, ConfigDict
from typing import Optional, Any


class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    ollama_status: str
    database_status: str


class AudioUploadResponse(BaseModel):
    audio_id: str
    filename: str
    status: str


class AnalysisStatusResponse(BaseModel):
    job_id: str
    status: str
    current_stage: Optional[str] = None
    progress: float
    error_message: Optional[str] = None


class AnalysisResultResponse(BaseModel):
    job_id: str
    status: str
    audio: Optional[dict] = None
    transcript: Optional[dict] = None
    analysis: Optional[dict] = None
    report: Optional[dict] = None
