# -*- coding: utf-8 -*-
# foxmask/task/schemas.py
# Pydantic schemas for task management

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import TaskStatus, TaskType, TaskPriority

class TaskBase(BaseModel):
    """Base task schema"""
    type: TaskType = Field(..., description="Task type")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload data")
    max_retries: int = Field(3, description="Maximum number of retries")
    scheduled_for: Optional[datetime] = Field(None, description="When the task should be executed")

class TaskCreate(TaskBase):
    """Task creation schema"""
    parent_task_id: Optional[str] = Field(None, description="Parent task ID if this is a subtask")

class TaskUpdate(BaseModel):
    """Task update schema"""
    priority: Optional[TaskPriority] = Field(None, description="Task priority")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    max_retries: Optional[int] = Field(None, description="Maximum number of retries")

class TaskInDB(TaskBase):
    """Task database schema"""
    id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Task status")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if task failed")
    retry_count: int = Field(..., description="Number of retry attempts")
    started_at: Optional[datetime] = Field(None, description="When the task started processing")
    completed_at: Optional[datetime] = Field(None, description="When the task completed")
    created_by: Optional[str] = Field(None, description="User ID who created the task")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID if this is a subtask")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True

class TaskStats(BaseModel):
    """Task statistics"""
    total_tasks: int = Field(..., description="Total number of tasks")
    pending_tasks: int = Field(..., description="Number of pending tasks")
    processing_tasks: int = Field(..., description="Number of processing tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")
    average_processing_time: Optional[float] = Field(None, description="Average processing time in seconds")

class TaskSearchResponse(BaseModel):
    """Task search response"""
    tasks: List[TaskInDB] = Field(..., description="Matching tasks")
    total_count: int = Field(..., description="Total number of matching tasks")