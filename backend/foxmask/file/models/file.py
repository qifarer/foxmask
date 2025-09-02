from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from typing import Union

class FileMetadata(BaseModel):
    date: str
    dirname: str
    filename: str
    path: str

class FileUploadState(BaseModel):
    progress: float
    rest_time: float
    speed: float

class UploadBase64ToS3Result(BaseModel):
    file_type: str
    hash: str
    metadata: FileMetadata
    size: int

class UploadResponse(BaseModel):
    data: Optional[FileMetadata] = None
    success: bool

class PreSignedUrlResponse(BaseModel):
    pre_sign_url: str
    metadata: FileMetadata

class FileCreateRequest(BaseModel):
    name: str
    file_type: str
    hash: str
    size: int
    url: str
    metadata: FileMetadata

class FileResponse(BaseModel):
    id: str
    name: str
    file_type: str
    hash: str
    size: int
    url: str
    metadata: FileMetadata
    created_at: datetime
    updated_at: datetime

class CheckFileHashResponse(BaseModel):
    is_exist: bool
    metadata: Optional[FileMetadata] = None
    url: Optional[str] = None
    
class UploadWithProgressResult(BaseModel):
    id: str
    url: str
    dimensions: Optional[Dict[str, int]] = None
    filename: Optional[str] = None

class UploadStatusUpdate(BaseModel):
    id: str
    type: str
    value: Optional[Dict[str, Any]] = None

class FileListResponse(BaseModel):
    files: List[FileResponse]
    total: int
    skip: int
    limit: int