# foxmask/document/models.py
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

class DocumentStatus(str, Enum):
    CREATING = "creating"
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VECTORIZING = "vectorizing"
    VECTORIZED = "vectorized"
    ERROR = "error"

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: DocumentStatus = DocumentStatus.CREATING
    file_ids: List[str]
    processed_file_ids: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    owner: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }