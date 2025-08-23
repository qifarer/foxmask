# app/domains/file/models.py
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import uuid

class FileStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class FileMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    size: int
    content_type: str
    status: FileStatus = FileStatus.UPLOADING
    owner: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileChunk(BaseModel):
    file_id: str
    chunk_index: int
    total_chunks: int
    chunk_data: bytes