# -*- coding: utf-8 -*-
# foxmask/task/models.py
# Task model definition using Beanie ODM for MongoDB

from beanie import Document
from pydantic import Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from foxmask.utils.helpers import get_current_time

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    KNOWLEDGE_PROCESSING = "knowledge_processing"
    FILE_PROCESSING = "file_processing"
    DATA_SYNC = "data_sync"
    SYSTEM_MAINTENANCE = "system_maintenance"
    NOTIFICATION = "notification"
    REPORT_GENERATION = "report_generation"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Task(Document):
    type: TaskType = Field(..., description="Task type")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    
    # Task data
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload data")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[str] = Field(None, description="Error message if task failed")
    
    # Metadata
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum number of retries")
    scheduled_for: Optional[datetime] = Field(None, description="When the task should be executed")
    started_at: Optional[datetime] = Field(None, description="When the task started processing")
    completed_at: Optional[datetime] = Field(None, description="When the task completed")
    
    # Relationships
    created_by: Optional[str] = Field(None, description="User ID who created the task")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID if this is a subtask")
    
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=get_current_time, description="Last update timestamp")
    
    class Settings:
        name = "tasks"
        indexes = [
            "type",
            "status",
            "priority",
            "scheduled_for",
            "created_by",
            "created_at",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "knowledge_processing",
                "status": "completed",
                "priority": "medium",
                "payload": {"knowledge_item_id": "item123"},
                "result": {"processed": True, "vector_id": "vec123"},
                "error": None,
                "retry_count": 0,
                "max_retries": 3,
                "scheduled_for": None,
                "started_at": "2023-01-01T10:00:00Z",
                "completed_at": "2023-01-01T10:05:00Z",
                "created_by": "user123",
                "parent_task_id": None,
                "created_at": "2023-01-01T09:55:00Z",
                "updated_at": "2023-01-01T10:05:00Z"
            }
        }
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = get_current_time()
    
    def start_processing(self):
        """Mark task as started"""
        self.status = TaskStatus.PROCESSING
        self.started_at = get_current_time()
        self.update_timestamp()
    
    def complete(self, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = get_current_time()
        self.update_timestamp()
    
    def fail(self, error: str):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = get_current_time()
        self.update_timestamp()
    
    def retry(self):
        """Increment retry count and reset status"""
        self.retry_count += 1
        if self.retry_count <= self.max_retries:
            self.status = TaskStatus.PENDING
            self.started_at = None
            self.update_timestamp()
        else:
            self.status = TaskStatus.FAILED
            self.completed_at = get_current_time()
            self.update_timestamp()