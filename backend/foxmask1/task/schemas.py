# foxmask/task/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from foxmask.task.models import TaskType, TaskStatus

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    document_id: str
    owner: str
    details: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    type: TaskType
    document_id: str
    details: Dict[str, Any] = {}