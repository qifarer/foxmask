# -*- coding: utf-8 -*-
# foxmask/shared/schemas.py
# Shared Pydantic schemas for common responses and requests

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(10, ge=1, le=100, description="Number of items to return")

class PaginatedResponse(BaseModel):
    """Paginated response schema"""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")
    has_more: bool = Field(..., description="Whether there are more items")

class SuccessResponse(BaseModel):
    """Success response schema"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")

class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")

class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(..., description="Dependency statuses")

class SearchQuery(BaseModel):
    """Search query parameters"""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")

class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    success: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")

class FileUploadRequest(BaseModel):
    """File upload request schema"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="File content type")
    description: Optional[str] = Field(None, description="File description")
    tags: List[str] = Field(default_factory=list, description="File tags")

class FileUploadResponse(BaseModel):
    """File upload response schema"""
    file_id: str = Field(..., description="File ID")
    upload_url: str = Field(..., description="Presigned upload URL")
    expires_at: datetime = Field(..., description="URL expiration time")

class Notification(BaseModel):
    """Notification schema"""
    id: str = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    read: bool = Field(False, description="Whether notification is read")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Notification metadata")