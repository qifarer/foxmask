from pydantic import BaseModel
from typing import Optional, Dict, Any

class UploadFileRequest(BaseModel):
    directory: Optional[str] = None
    pathname: Optional[str] = None
    skip_check_file_type: bool = False

class UploadBase64Request(BaseModel):
    base64_data: str
    filename: Optional[str] = None
    directory: Optional[str] = None
    pathname: Optional[str] = None

class UploadDataRequest(BaseModel):
    data: Dict[str, Any]
    filename: Optional[str] = None
    directory: Optional[str] = None
    pathname: Optional[str] = None

class PresignedUrlRequest(BaseModel):
    filename: str
    directory: Optional[str] = None
    pathname: Optional[str] = None

class UploadWithProgressRequest(BaseModel):
    knowledge_base_id: Optional[str] = None
    skip_check_file_type: bool = False