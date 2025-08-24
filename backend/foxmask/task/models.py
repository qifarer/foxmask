# backend/foxmask/task/models.py
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class TaskType(str, Enum):
    DOCUMENT_PARSING = "document_parsing"
    VECTORIZATION = "vectorization"
    RELATION_EXTRACTION = "relation_extraction"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    document_id: str
    owner: str
    details: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True