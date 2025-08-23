# app/domains/document/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    file_ids: List[str] = Field(..., min_items=1)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    file_ids: List[str]
    processed_file_ids: Optional[List[str]] = None
    owner: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None