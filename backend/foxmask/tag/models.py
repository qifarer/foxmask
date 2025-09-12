# -*- coding: utf-8 -*-
# foxmask/tag/models.py
# Beanie document model for tag management

from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
from foxmask.utils.helpers import get_current_time

class TagType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    AUTOMATED = "automated"

class Tag(Document):
    name: str = Field(..., description="Tag name")
    type: TagType = Field(TagType.USER, description="Tag type")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field("#6B7280", description="Tag color code")
    usage_count: int = Field(0, description="Number of times this tag is used")
    
    # Relationships
    created_by: Optional[str] = Field(None, description="User ID who created the tag")
    related_tags: List[str] = Field(default_factory=list, description="Related tag IDs")
    
    # Metadata
    is_active: bool = Field(True, description="Is tag active")
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=get_current_time, description="Last update timestamp")
    
    class Settings:
        name = "tags"
        indexes = [
            "name",
            "type",
            "created_by",
            "is_active",
            "usage_count",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "machine-learning",
                "type": "user",
                "description": "Machine learning related content",
                "color": "#3B82F6",
                "usage_count": 42,
                "created_by": "user123",
                "related_tags": ["tag456", "tag789"],
                "is_active": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = get_current_time()
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.update_timestamp()
    
    def decrement_usage(self):
        """Decrement usage count"""
        if self.usage_count > 0:
            self.usage_count -= 1
            self.update_timestamp()