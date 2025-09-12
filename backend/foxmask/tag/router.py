# -*- coding: utf-8 -*-
# foxmask/tag/router.py
# API router for tag management

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Annotated, List, Optional

from .services import tag_service
from .models import Tag, TagType
from .schemas import TagCreate, TagInDB, TagUpdate, TagUsageStats, TagSearchResponse
from foxmask.shared.dependencies import (
    get_user_from_token, require_read, require_write, require_delete, require_admin,
    get_api_context
)
from foxmask.core.logger import logger

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=TagInDB)
async def create_tag(
    request: Request,
    tag_data: TagCreate,
    api_key_info: dict = Depends(get_user_from_token)
):
    """Create a new tag"""
    return await tag_service.create_tag(tag_data, api_key_info["casdoor_user_id"])

@router.get("/{tag_id}", response_model=TagInDB)
async def get_tag(
    request: Request,
    tag_id: str,
    api_key_info: dict = Depends(get_user_from_token)
):
    """Get tag by ID"""
    tag = await tag_service.get_tag(tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return tag

@router.put("/{tag_id}", response_model=TagInDB)
async def update_tag(
    request: Request,
    tag_id: str,
    update_data: TagUpdate,
    api_key_info: dict = Depends(get_user_from_token)
):
    """Update tag"""
    # First check if tag exists
    existing_tag = await tag_service.get_tag(tag_id)
    if not existing_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check permission - only creator or admin can update
    if (existing_tag.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tag"
        )
    
    tag = await tag_service.update_tag(tag_id, update_data, api_key_info["casdoor_user_id"])
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return tag

@router.delete("/{tag_id}")
async def delete_tag(
    request: Request,
    tag_id: str,
    api_key_info: dict = Depends(get_user_from_token)
):
    """Delete tag"""
   
    # First check if tag exists
    existing_tag = await tag_service.get_tag(tag_id)
    if not existing_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check permission - only creator or admin can delete
    if (existing_tag.created_by != api_key_info["casdoor_user_id"] and 
        "admin" not in api_key_info["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this tag"
        )
    
    success = await tag_service.delete_tag(tag_id, api_key_info["casdoor_user_id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return {"message": "Tag deleted successfully"}

@router.get("/", response_model=List[TagInDB])
async def list_tags(
    request: Request,
    api_key_info: dict = Depends(get_user_from_token),
    skip: int = 0,
    limit: int = 10,
    type: Optional[TagType] = None
):
    """List tags with optional filtering"""
    logger.warning(f"Listing tags with type: {type}, skip: {skip}, api_key_info: {api_key_info}")
    if type:
        return await tag_service.search_tags("", type, skip, limit)
    return await tag_service.search_tags("", None, skip, limit)

@router.get("/search/{query}", response_model=TagSearchResponse)
async def search_tags(
    request: Request,
    query: str,
    api_key_info: dict = Depends(get_user_from_token),
    type: Optional[TagType] = None,
    skip: int = 0,
    limit: int = 10
):
    """Search tags by name"""
    tags = await tag_service.search_tags(query, type, skip, limit)
    
    # Build filter for total count
    filter_condition = {"name": {"$regex": query, "$options": "i"}}
    if type:
        filter_condition["type"] = type
    
    total_count = await Tag.find(filter_condition).count()
    
    return TagSearchResponse(tags=tags, total_count=total_count)

@router.get("/popular", response_model=List[TagInDB])
async def get_popular_tags(
    request: Request,
    api_key_info: dict = Depends(require_read),
    limit: int = 20
):
    """Get most popular tags"""
    return await tag_service.get_popular_tags(limit)

@router.get("/user/mine", response_model=List[TagInDB])
async def get_my_tags(
    request: Request,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 10
):
    """Get tags created by current user"""
    return await tag_service.get_user_tags(api_key_info["casdoor_user_id"], skip, limit)

@router.get("/system/all", response_model=List[TagInDB])
async def get_system_tags(
    request: Request,
    api_key_info: dict = Depends(require_admin)
):
    """Get all system tags (admin only)"""
    # Admin check is handled by require_admin dependency
    return await tag_service.get_system_tags()

@router.post("/{tag_id}/increment-usage")
async def increment_tag_usage(
    request: Request,
    tag_id: str,
    api_key_info: dict = Depends(require_write)
):
    """Increment tag usage count"""
    success = await tag_service.increment_tag_usage(tag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return {"message": "Tag usage incremented"}

@router.post("/{tag_id}/decrement-usage")
async def decrement_tag_usage(
    request: Request,
    tag_id: str,
    api_key_info: dict = Depends(require_write)
):
    """Decrement tag usage count"""
    success = await tag_service.decrement_tag_usage(tag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return {"message": "Tag usage decremented"}

@router.get("/stats/usage", response_model=List[TagUsageStats])
async def get_tag_usage_stats(
    request: Request,
    api_key_info: dict = Depends(require_read),
    limit: int = 50
):
    """Get tag usage statistics"""
    # Only admin users can access usage statistics
    if "admin" not in api_key_info["permissions"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for usage statistics"
        )
    
    return await tag_service.get_tag_usage_stats(limit)

@router.get("/types/{tag_type}", response_model=List[TagInDB])
async def get_tags_by_type(
    request: Request,
    tag_type: TagType,
    api_key_info: dict = Depends(require_read),
    skip: int = 0,
    limit: int = 50
):
    """Get tags by specific type"""
    return await tag_service.get_tags_by_type(tag_type, skip, limit)

@router.get("/api-key/info")
async def get_api_key_info(
    request: Request,
    api_key_info: dict = Depends(get_api_context)
):
    """Get information about the current API key"""
    return api_key_info