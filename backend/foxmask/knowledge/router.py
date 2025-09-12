# -*- coding: utf-8 -*-
# foxmask/knowledge/router.py
# FastAPI router for knowledge item and knowledge base management

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Annotated, List, Optional, Dict

from .services.knowledge_item import knowledge_item_service
from .services.knowledge_base import knowledge_base_service
from .schemas import (
    KnowledgeItemCreate, KnowledgeItemInDB, KnowledgeItemUpdate,
    KnowledgeBaseCreate, KnowledgeBaseInDB, KnowledgeBaseUpdate,
    KnowledgeProcessingRequest, KnowledgeProcessingResponse
)
from .services.vector_search import vector_search_service
from .services.knowledge_graph import knowledge_graph_service
from .schemas import SearchQuery, SearchResponse, RecommendationResponse

from foxmask.shared.dependencies import (
    validate_api_key_access, require_read, require_write, require_delete, require_admin,
    get_api_context
)
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Knowledge Item Routes
@router.post("/items", response_model=KnowledgeItemInDB)
async def create_knowledge_item(
    request: Request,
    item_data: KnowledgeItemCreate,
    api_key_info: dict = Depends(require_write)
):
    """Create a new knowledge item"""
    return await knowledge_item_service.create_knowledge_item(
        item_data, api_key_info["casdoor_user_id"]
    )

@router.get("/items/{item_id}", response_model=KnowledgeItemInDB)
async def get_knowledge_item(
    request: Request,
    item_id: str,
    api_key_info: dict = Depends(require_read)
):
    """Get knowledge item by ID"""
    knowledge_item = await knowledge_item_service.get_knowledge_item(item_id)
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check permission - only creator or admin can access
    if (knowledge_item.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this knowledge item"
        )
    
    return knowledge_item

@router.put("/items/{item_id}", response_model=KnowledgeItemInDB)
async def update_knowledge_item(
    request: Request,
    item_id: str,
    update_data: KnowledgeItemUpdate,
    api_key_info: dict = Depends(require_write)
):
    """Update knowledge item"""
    # First check if item exists and user has permission
    knowledge_item = await knowledge_item_service.get_knowledge_item(item_id)
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check permission
    if (knowledge_item.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this knowledge item"
        )
    
    return await knowledge_item_service.update_knowledge_item(
        item_id, update_data, api_key_info["casdoor_user_id"]
    )

@router.delete("/items/{item_id}")
async def delete_knowledge_item(
    request: Request,
    item_id: str,
    api_key_info: dict = Depends(require_delete)
):
    """Delete knowledge item"""
    # First check if item exists and user has permission
    knowledge_item = await knowledge_item_service.get_knowledge_item(item_id)
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check permission
    if (knowledge_item.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this knowledge item"
        )
    
    success = await knowledge_item_service.delete_knowledge_item(
        item_id, api_key_info["casdoor_user_id"]
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    return {"message": "Knowledge item deleted successfully"}

@router.get("/items", response_model=List[KnowledgeItemInDB])
async def list_knowledge_items(
    request: Request,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 10
):
    """List user's knowledge items"""
    return await knowledge_item_service.list_user_knowledge_items(
        api_key_info["casdoor_user_id"], skip, limit
    )

# Knowledge Base Routes
@router.post("/bases", response_model=KnowledgeBaseInDB)
async def create_knowledge_base(
    request: Request,
    kb_data: KnowledgeBaseCreate,
    api_key_info: dict = Depends(require_write)
):
    """Create a new knowledge base"""
    return await knowledge_base_service.create_knowledge_base(
        kb_data, api_key_info["casdoor_user_id"]
    )

@router.get("/bases/{kb_id}", response_model=KnowledgeBaseInDB)
async def get_knowledge_base(
    request: Request,
    kb_id: str,
    api_key_info: dict = Depends(require_read)
):
    """Get knowledge base by ID"""
    knowledge_base = await knowledge_base_service.get_knowledge_base(kb_id)
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Check permission - creator, public access, or admin
    if (knowledge_base.created_by != api_key_info["casdoor_user_id"] and 
        not knowledge_base.is_public and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this knowledge base"
        )
    
    return knowledge_base

@router.put("/bases/{kb_id}", response_model=KnowledgeBaseInDB)
async def update_knowledge_base(
    request: Request,
    kb_id: str,
    update_data: KnowledgeBaseUpdate,
    api_key_info: dict = Depends(require_write)
):
    """Update knowledge base"""
    # First check if base exists and user has permission
    knowledge_base = await knowledge_base_service.get_knowledge_base(kb_id)
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Check permission
    if (knowledge_base.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this knowledge base"
        )
    
    return await knowledge_base_service.update_knowledge_base(
        kb_id, update_data, api_key_info["casdoor_user_id"]
    )

@router.delete("/bases/{kb_id}")
async def delete_knowledge_base(
    request: Request,
    kb_id: str,
    api_key_info: dict = Depends(require_delete)
):
    """Delete knowledge base"""
    # First check if base exists and user has permission
    knowledge_base = await knowledge_base_service.get_knowledge_base(kb_id)
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Check permission
    if (knowledge_base.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this knowledge base"
        )
    
    success = await knowledge_base_service.delete_knowledge_base(
        kb_id, api_key_info["casdoor_user_id"]
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    return {"message": "Knowledge base deleted successfully"}

@router.get("/bases", response_model=List[KnowledgeBaseInDB])
async def list_knowledge_bases(
    request: Request,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 10
):
    """List user's knowledge bases"""
    return await knowledge_base_service.list_user_knowledge_bases(
        api_key_info["casdoor_user_id"], skip, limit
    )

@router.get("/bases/public", response_model=List[KnowledgeBaseInDB])
async def list_public_knowledge_bases(
    request: Request,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 10
):
    """List public knowledge bases"""
    return await knowledge_base_service.list_public_knowledge_bases(skip, limit)

@router.get("/bases/{kb_id}/items", response_model=List[KnowledgeItemInDB])
async def get_knowledge_base_items(
    request: Request,
    kb_id: str,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 10
):
    """Get knowledge items in a knowledge base"""
    knowledge_base = await knowledge_base_service.get_knowledge_base(kb_id)
    if not knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Check permission
    if (knowledge_base.created_by != api_key_info["casdoor_user_id"] and 
        not knowledge_base.is_public and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this knowledge base"
        )
    
    return await knowledge_base_service.get_knowledge_base_items(kb_id, skip, limit)

@router.post("/process", response_model=KnowledgeProcessingResponse)
async def process_knowledge_item(
    request: Request,
    process_request: KnowledgeProcessingRequest,
    api_key_info: dict = Depends(require_write)
):
    """Trigger processing for a knowledge item"""
    knowledge_item = await knowledge_item_service.get_knowledge_item(process_request.knowledge_item_id)
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Check permission
    if (knowledge_item.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to process this knowledge item"
        )
    
    # Send processing message
    message = {
        "knowledge_item_id": process_request.knowledge_item_id,
        "process_types": process_request.process_types,
        "api_key_id": api_key_info["api_key_id"]
    }
    
    await kafka_manager.send_message(settings.KAFKA_KNOWLEDGE_TOPIC, message)
    
    return KnowledgeProcessingResponse(
        message="Processing started",
        knowledge_item_id=process_request.knowledge_item_id,
        status="processing"
    )

# Search and Recommendation Routes
@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: Request,
    search_query: SearchQuery,
    api_key_info: dict = Depends(require_read),
    limit: int = Query(10, ge=1, le=100),
    certainty: float = Query(0.7, ge=0.0, le=1.0)
):
    """Perform semantic search on knowledge items"""
    try:
        # Add user-based filtering to search
        filters = search_query.filters or {}
        if "admin" not in api_key_info["permissions"]:
            # Non-admin users can only search their own items and public items
            filters["user_filter"] = {
                "created_by": api_key_info["casdoor_user_id"],
                "is_public": True
            }
        
        results = await vector_search_service.semantic_search(
            query=search_query.query,
            filters=filters,
            limit=limit,
            certainty=certainty
        )
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=search_query.query
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e}"
        )

@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: Request,
    search_query: SearchQuery,
    api_key_info: dict = Depends(require_read),
    limit: int = Query(10, ge=1, le=100),
    alpha: float = Query(0.5, ge=0.0, le=1.0)
):
    """Perform hybrid search (vector + keyword)"""
    try:
        # Add user-based filtering to search
        filters = search_query.filters or {}
        if "admin" not in api_key_info["permissions"]:
            filters["user_filter"] = {
                "created_by": api_key_info["casdoor_user_id"],
                "is_public": True
            }
        
        results = await vector_search_service.hybrid_search(
            query=search_query.query,
            filters=filters,
            limit=limit,
            alpha=alpha
        )
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=search_query.query
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {e}"
        )

@router.get("/{item_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: Request,
    item_id: str,
    api_key_info: dict = Depends(require_read),
    limit: int = Query(10, ge=1, le=20)
):
    """Get recommendations for similar content"""
    try:
        # First check if user has access to the source item
        source_item = await knowledge_item_service.get_knowledge_item(item_id)
        if not source_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source knowledge item not found"
            )
        
        if (source_item.created_by != api_key_info["casdoor_user_id"] and 
            not getattr(source_item, 'is_public', False) and 
            "admin" not in api_key_info["permissions"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this knowledge item"
            )
        
        # Get vector-based recommendations with user filtering
        vector_recommendations = await vector_search_service.find_similar_items(
            knowledge_item_id=item_id,
            user_id=api_key_info["casdoor_user_id"],
            is_admin="admin" in api_key_info["permissions"],
            limit=limit
        )
        
        # Get graph-based recommendations
        graph_recommendations = await knowledge_graph_service.recommend_related_content(
            knowledge_item_id=item_id,
            user_id=api_key_info["casdoor_user_id"],
            is_admin="admin" in api_key_info["permissions"],
            limit=limit
        )
        
        return RecommendationResponse(
            vector_based=vector_recommendations,
            graph_based=graph_recommendations,
            total_recommendations=len(vector_recommendations) + len(graph_recommendations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {e}"
        )

@router.get("/graph/insights")
async def get_knowledge_graph_insights(
    request: Request,
    api_key_info: dict = Depends(require_read)
):
    """Get insights from the knowledge graph"""
    try:
        # Only admin users can access global insights
        if "admin" not in api_key_info["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required for graph insights"
            )
        
        insights = await knowledge_graph_service.get_knowledge_graph_insights()
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph insights: {e}"
        )

@router.get("/vector/stats")
async def get_vector_index_stats(
    request: Request,
    api_key_info: dict = Depends(require_read)
):
    """Get statistics about the vector index"""
    try:
        # Only admin users can access global stats
        if "admin" not in api_key_info["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required for vector statistics"
            )
        
        stats = await vector_search_service.get_index_statistics()
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vector stats: {e}"
        )

# API Key specific endpoints
@router.get("/api-key/info")
async def get_api_key_info(
    request: Request,
    api_key_info: dict = Depends(get_api_context)
):
    """Get information about the current API key"""
    return api_key_info