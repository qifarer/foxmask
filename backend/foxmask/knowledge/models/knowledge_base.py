from beanie import Document
from pydantic import Field
from typing import Optional, List
from datetime import datetime
from foxmask.utils.helpers import get_current_time

class KnowledgeBase(Document):
    name: str = Field(..., description="Knowledge base name")
    description: Optional[str] = Field(None, description="Description")
    is_public: bool = Field(False, description="Is knowledge base public")
    tags: List[str] = Field(default_factory=list, description="Tags")
    category: Optional[str] = Field(None, description="Category")
    
    # Statistics
    item_count: int = Field(0, description="Number of knowledge items")
    
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=get_current_time, description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class Settings:
        name = "knowledge_bases"
        indexes = [
            "is_public",
            "tags",
            "created_by",
            "created_at",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "AI Research",
                "description": "Collection of AI research papers and resources",
                "is_public": True,
                "tags": ["ai", "research", "papers"],
                "category": "Technology",
                "item_count": 50,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "user123"
            }
        }
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = get_current_time()
    
    def increment_item_count(self):
        """Increment item count"""
        self.item_count += 1
        self.update_timestamp()
    
    def decrement_item_count(self):
        """Decrement item count"""
        if self.item_count > 0:
            self.item_count -= 1
            self.update_timestamp()