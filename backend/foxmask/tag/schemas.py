# -*- coding: utf-8 -*-
# foxmask/tag/schemas.py
# Pydantic schemas for tag management

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .models import TagType

class TagBase(BaseModel):
    """Base tag schema"""
    name: str = Field(..., description="Tag name")
    type: TagType = Field(TagType.USER, description="Tag type")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field("#6B7280", description="Tag color code")

class TagCreate(TagBase):
    """Tag creation schema"""
    related_tags: List[str] = Field(default_factory=list, description="Related tag IDs")

class TagUpdate(BaseModel):
    """Tag update schema"""
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, description="Tag color code")
    related_tags: Optional[List[str]] = Field(None, description="Related tag IDs")
    is_active: Optional[bool] = Field(None, description="Is tag active")

class TagInDB(TagBase):
    """Tag database schema"""
    id: str = Field(..., description="Tag ID")
    usage_count: int = Field(..., description="Number of times this tag is used")
    created_by: Optional[str] = Field(None, description="User ID who created the tag")
    related_tags: List[str] = Field(..., description="Related tag IDs")
    is_active: bool = Field(..., description="Is tag active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True

class TagUsageStats(BaseModel):
    """Tag usage statistics"""
    tag_id: str = Field(..., description="Tag ID")
    tag_name: str = Field(..., description="Tag name")
    usage_count: int = Field(..., description="Usage count")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")

class TagSearchResponse(BaseModel):
    """Tag search response"""
    tags: List[TagInDB] = Field(..., description="Matching tags")
    total_count: int = Field(..., description="Total number of matching tags")