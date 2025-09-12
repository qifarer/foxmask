from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from foxmask.utils.helpers import get_current_time

class KnowledgeItemStatus(str, Enum):
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VECTORIZING = "vectorizing"
    VECTORIZED = "vectorized"
    GRAPHING = "graphing"
    COMPLETED = "completed"
    FAILED = "failed"

class KnowledgeItemType(str, Enum):
    FILE = "file"
    WEBPAGE = "webpage"
    API = "api"
    CHAT = "chat"
    PRODUCT = "product"
    BRAND = "brand"
    CUSTOM = "custom"

class KnowledgeItem(Document):
    title: str = Field(..., description="Knowledge item title")
    description: Optional[str] = Field(None, description="Description")
    type: KnowledgeItemType = Field(..., description="Knowledge item type")
    status: KnowledgeItemStatus = Field(KnowledgeItemStatus.CREATED, description="Processing status")
    
    # Source information
    source_urls: List[str] = Field(default_factory=list, description="Source URLs")
    file_ids: List[str] = Field(default_factory=list, description="Related file IDs")
    
    # Processed data
    parsed_content: Optional[Dict] = Field(None, description="Parsed content (MD/JSON)")
    vector_id: Optional[str] = Field(None, description="Weaviate vector ID")
    graph_id: Optional[str] = Field(None, description="Neo4j graph node ID")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags")
    knowledge_base_ids: List[str] = Field(default_factory=list, description="Knowledge base IDs")
    category: Optional[str] = Field(None, description="Category")
    
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=get_current_time, description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class Settings:
        name = "knowledge_items"
        indexes = [
            "type",
            "status",
            "tags",
            "knowledge_base_ids",
            "created_by",
            "created_at",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Introduction to AI",
                "description": "A comprehensive guide to artificial intelligence",
                "type": "file",
                "status": "completed",
                "source_urls": ["https://example.com/ai-guide.pdf"],
                "file_ids": ["file123"],
                "parsed_content": {"content": "Markdown content here..."},
                "vector_id": "vector123",
                "graph_id": "node123",
                "tags": ["ai", "machine learning", "guide"],
                "knowledge_base_ids": ["kb123"],
                "category": "Technology",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "user123"
            }
        }
    
    def update_status(self, status: KnowledgeItemStatus):
        """Update knowledge item status"""
        self.status = status
        self.updated_at = get_current_time()
    
    def add_to_knowledge_base(self, knowledge_base_id: str):
        """Add knowledge item to a knowledge base"""
        if knowledge_base_id not in self.knowledge_base_ids:
            self.knowledge_base_ids.append(knowledge_base_id)
            self.updated_at = get_current_time()
    
    def remove_from_knowledge_base(self, knowledge_base_id: str):
        """Remove knowledge item from a knowledge base"""
        if knowledge_base_id in self.knowledge_base_ids:
            self.knowledge_base_ids.remove(knowledge_base_id)
            self.updated_at = get_current_time()