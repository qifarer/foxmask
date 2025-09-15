from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    """Kafka message types"""
    KNOWLEDGE_PROCESSING = "knowledge_processing"
    FILE_PROCESSING = "file_processing"
    NOTIFICATION = "notification"
    SYSTEM_EVENT = "system_event"
    DATA_SYNC = "data_sync"

class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class BaseMessage(BaseModel):
    """Base Kafka message schema"""
    message_id: str = Field(..., description="Unique message ID")
    type: MessageType = Field(..., description="Message type")
    priority: MessagePriority = Field(MessagePriority.NORMAL, description="Message priority")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message creation time")
    source: str = Field(..., description="Message source service")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class KnowledgeItemMessage(BaseMessage):
    """Knowledge processing message schema"""
    knowledge_item_id: str = Field(..., description="Knowledge item ID to process")
    process_types: List[str] = Field(..., description="Types of processing to perform")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum number of retries")

class KnowledgeProcessingMessage(BaseMessage):
    """Knowledge processing message schema"""
    knowledge_item_id: str = Field(..., description="Knowledge item ID to process")
    process_types: List[str] = Field(..., description="Types of processing to perform")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum number of retries")

class FileProcessingMessage(BaseMessage):
    """File processing message schema"""
    file_id: str = Field(..., description="File ID to process")
    processing_type: str = Field(..., description="Type of processing to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")

class NotificationMessage(BaseMessage):
    """Notification message schema"""
    user_id: str = Field(..., description="Target user ID")
    notification_type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Notification data")

class SystemEventMessage(BaseMessage):
    """System event message schema"""
    event_type: str = Field(..., description="Event type")
    component: str = Field(..., description="Component that generated the event")
    severity: str = Field("info", description="Event severity")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")

class DataSyncMessage(BaseMessage):
    """Data synchronization message schema"""
    sync_type: str = Field(..., description="Synchronization type")
    entity_type: str = Field(..., description="Entity type to sync")
    entity_ids: List[str] = Field(..., description="Entity IDs to sync")
    direction: str = Field("both", description="Sync direction")