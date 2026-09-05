from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class AudioFileBase(BaseModel):
    filename: str
    file_path: str
    file_size: Optional[float] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None


class AudioFileCreate(AudioFileBase):
    pass


class AudioFileUpdate(BaseModel):
    status: Optional[str] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    error_message: Optional[str] = None


class AudioFileResponse(AudioFileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
