# -*- coding: utf-8 -*-
# foxmask/knowledge/schemas.py
# Pydantic schemas for knowledge items and knowledge bases

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models.knowledge_item import KnowledgeItemStatus, KnowledgeItemType
from .models.knowledge_base import KnowledgeBase

class KnowledgeItemBase(BaseModel):
    """Base knowledge item schema"""
    title: str = Field(..., description="Knowledge item title")
    description: Optional[str] = Field(None, description="Description")
    type: KnowledgeItemType = Field(..., description="Knowledge item type")
    source_urls: List[str] = Field(default_factory=list, description="Source URLs")
    file_ids: List[str] = Field(default_factory=list, description="Related file IDs")
    tags: List[str] = Field(default_factory=list, description="Tags")
    category: Optional[str] = Field(None, description="Category")

class KnowledgeItemCreate(KnowledgeItemBase):
    """Knowledge item creation schema"""
    knowledge_base_ids: List[str] = Field(default_factory=list, description="Knowledge base IDs")

class KnowledgeItemUpdate(BaseModel):
    """Knowledge item update schema"""
    title: Optional[str] = Field(None, description="Knowledge item title")
    description: Optional[str] = Field(None, description="Description")
    tags: Optional[List[str]] = Field(None, description="Tags")
    category: Optional[str] = Field(None, description="Category")

class KnowledgeItemInDB(KnowledgeItemBase):
    """Knowledge item database schema"""
    id: str = Field(..., description="Knowledge item ID")
    status: KnowledgeItemStatus = Field(..., description="Processing status")
    parsed_content: Optional[Dict] = Field(None, description="Parsed content (MD/JSON)")
    vector_id: Optional[str] = Field(None, description="Weaviate vector ID")
    graph_id: Optional[str] = Field(None, description="Neo4j graph node ID")
    knowledge_base_ids: List[str] = Field(..., description="Knowledge base IDs")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class ConfigDict:
        from_attributes = True

class KnowledgeBaseBase(BaseModel):
    """Base knowledge base schema"""
    name: str = Field(..., description="Knowledge base name")
    description: Optional[str] = Field(None, description="Description")
    is_public: bool = Field(False, description="Is knowledge base public")
    tags: List[str] = Field(default_factory=list, description="Tags")
    category: Optional[str] = Field(None, description="Category")

class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Knowledge base creation schema"""
    pass

class KnowledgeBaseUpdate(BaseModel):
    """Knowledge base update schema"""
    name: Optional[str] = Field(None, description="Knowledge base name")
    description: Optional[str] = Field(None, description="Description")
    is_public: Optional[bool] = Field(None, description="Is knowledge base public")
    tags: Optional[List[str]] = Field(None, description="Tags")
    category: Optional[str] = Field(None, description="Category")

class KnowledgeBaseInDB(KnowledgeBaseBase):
    """Knowledge base database schema"""
    id: str = Field(..., description="Knowledge base ID")
    item_count: int = Field(..., description="Number of knowledge items")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class ConfigDict:
        from_attributes = True

class KnowledgeProcessingRequest(BaseModel):
    """Knowledge processing request schema"""
    knowledge_item_id: str = Field(..., description="Knowledge item ID to process")
    process_types: List[str] = Field(..., description="Types of processing to perform")

class KnowledgeProcessingResponse(BaseModel):
    """Knowledge processing response schema"""
    message: str = Field(..., description="Processing message")
    knowledge_item_id: str = Field(..., description="Knowledge item ID")
    status: str = Field(..., description="Processing status")

class SearchResultItem(BaseModel):
    """Search result item schema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Knowledge item ID")
    title: str = Field(..., description="Item title")
    description: Optional[str] = Field(None, description="Item description")
    type: Optional[str] = Field(None, description="Item type")
    category: Optional[str] = Field(None, description="Item category")
    tags: List[str] = Field(default_factory=list, description="Item tags")
    certainty: Optional[float] = Field(None, description="Search certainty score", ge=0.0, le=1.0)
    distance: Optional[float] = Field(None, description="Vector distance")
    score: Optional[float] = Field(None, description="Hybrid search score")
    weaviate_id: Optional[str] = Field(None, description="Weaviate object ID")

class SearchResponse(BaseModel):
    """Search response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    results: List[SearchResultItem] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")
    processing_time_ms: Optional[float] = Field(None, description="Search processing time in milliseconds")
    has_more: bool = Field(False, description="Whether there are more results")

class RecommendationItem(BaseModel):
    """Recommendation item schema"""
    model_config = ConfigDict(from_attributes=True)
    
    item_id: str = Field(..., description="Recommended item ID")
    title: str = Field(..., description="Item title")
    description: Optional[str] = Field(None, description="Item description")
    similarity_score: Optional[float] = Field(None, description="Similarity score")
    common_tags: Optional[int] = Field(None, description="Number of common tags")
    common_bases: Optional[int] = Field(None, description="Number of common knowledge bases")
    recommendation_type: str = Field(..., description="Type of recommendation (vector_based, graph_based)")

class RecommendationResponse(BaseModel):
    """Recommendation response schema"""
    model_config = ConfigDict(from_attributes=True)
    
    vector_based: List[RecommendationItem] = Field(..., description="Vector-based recommendations")
    graph_based: List[RecommendationItem] = Field(..., description="Graph-based recommendations")
    total_recommendations: int = Field(..., description="Total number of recommendations")
    source_item_id: str = Field(..., description="ID of the source item")

class SearchQuery(BaseModel):
    """Search query parameters"""
    model_config = ConfigDict(from_attributes=True)
    
    query: str = Field(..., description="Search query text")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    use_semantic_search: bool = Field(True, description="Whether to use semantic search")
    use_keyword_search: bool = Field(True, description="Whether to use keyword search")   