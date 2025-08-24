# foxmask/file/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str

class FileListResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    status: str
    uploaded_at: datetime
    url: Optional[str] = None

    class Config:
        from_attributes = True