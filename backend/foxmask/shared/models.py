# -*- coding: utf-8 -*-
# foxmask/shared/models.py
# Shared models and enums for the Foxmask application

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class Status(str, Enum):
    """Common status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"

class Permission(str, Enum):
    """Common permissions enum"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SHARE = "share"

class AuditBase(BaseModel):
    """Base audit fields"""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    updated_by: Optional[str] = Field(None, description="Last updater user ID")

class MetadataBase(BaseModel):
    """Base metadata fields"""
    tags: List[str] = Field(default_factory=list, description="Tags")
    description: Optional[str] = Field(None, description="Description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PaginationInfo(BaseModel):
    """Pagination information"""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

class SearchResult(BaseModel):
    """Search result"""
    items: List[Any] = Field(..., description="Search results")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    facets: Optional[Dict[str, Any]] = Field(None, description="Search facets")

class SystemInfo(BaseModel):
    """System information"""
    version: str = Field(..., description="System version")
    name: str = Field(..., description="System name")
    environment: str = Field(..., description="Environment")
    uptime: float = Field(..., description="System uptime in seconds")
    timestamp: datetime = Field(..., description="Info timestamp")

class HealthStatus(BaseModel):
    """Health status"""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    message: Optional[str] = Field(None, description="Status message")
    timestamp: datetime = Field(..., description="Check timestamp")

class APIResponse(BaseModel):
    """Generic API response"""
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")

class BulkOperationResult(BaseModel):
    """Bulk operation result"""
    processed: int = Field(..., description="Number of processed items")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")