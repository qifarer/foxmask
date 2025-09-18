import uuid
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import json

class MessageTopicEnum(str, Enum):
    """Kafka message topics"""
    KB_PROCESSING = "kb_processing"
    NOTIFICATIONS = "notifications"
    SYSTEM_EVENTS = "system_events"
    BIZ_DATA_SYNC = "biz_data_sync"

    def __str__(self):
        return self.value
    
class MessageEventTypeEnum(str, Enum):
    """Kafka message event types"""
    CREATE_ITEM_FROM_FILE = "create_item_from_file"
    CREATE_ITEM_FROM_CHAT = "create_item_from_chat"
    PARSE_MD_FROM_SOURCE = "parse_md_from_source"
    PARSE_JSON_FROM_SOURCE = "parse_json_from_source"
    VECTORIZED_KNOWLEDGE = "vectorized_knowledge"
    GRAPH_KNOWLEDGE = "graph_knowledge"
    
    def __str__(self):
        return self.value
    

class MessagePriorityEnum(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self):
        return self.value

class BaseMessage(BaseModel):
    """Base Kafka message schema"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")
    key: str = Field(..., description="Message biz key")
    topic: MessageTopicEnum = Field(..., description="Message topic")
    type: MessageEventTypeEnum = Field(..., description="Message event type")
    priority: MessagePriorityEnum = Field(default=MessagePriorityEnum.NORMAL, description="Message priority")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message creation time in UTC")
    source: str = Field(..., description="Message source service")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v: Optional[str]) -> str:
        """
        验证和生成消息ID
        
        Args:
            v: 输入的ID值，如果为None则自动生成
            
        Returns:
            有效的UUID字符串
        """
        if v is None:
            return str(uuid.uuid4())
        if isinstance(v, str) and v.strip():
            # 验证是否为有效的UUID格式
            try:
                uuid.UUID(v)
                return v
            except ValueError:
                # 如果不是有效的UUID，生成新的
                return str(uuid.uuid4())
        return str(uuid.uuid4())

    def to_dict(self, exclude_none: bool = True, exclude_unset: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Convert model to dictionary with various options
        
        Args:
            exclude_none: Whether to exclude fields with None values
            exclude_unset: Whether to exclude fields that were not explicitly set
            **kwargs: Additional arguments for model_dump method
            
        Returns:
            Dictionary representation of the model
        """
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            **kwargs
        )

    def to_json(self, indent: int = 2, **kwargs) -> str:
        """
        Convert model to JSON string
        
        Args:
            indent: JSON indentation level
            **kwargs: Additional arguments for model_dump_json method
            
        Returns:
            JSON string representation of the model
        """
        return self.model_dump_json(indent=indent, **kwargs)

    def generate_new_id(self) -> None:
        """
        为消息生成新的ID
        """
        self.id = str(uuid.uuid4())

    @classmethod
    def create_with_id(cls, id: Optional[str] = None, **kwargs) -> 'BaseMessage':
        """
        创建消息实例，可选择性指定ID
        
        Args:
            id: 可选的ID，如果未提供则自动生成
            **kwargs: 其他字段参数
            
        Returns:
            BaseMessage实例
        """
        if id is not None:
            kwargs['id'] = id
        return cls(**kwargs)

class KnowledgeProcessingMessage(BaseMessage):
    """Knowledge processing message schema"""
    tenant: str = Field(..., description="Tenant ID")
    user: str = Field(..., description="User ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Processing data")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    def to_kafka_payload(self, exclude_none: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Convert to Kafka message payload format with additional metadata
        
        Args:
            exclude_none: Whether to exclude None values
            **kwargs: Additional arguments for to_dict method
            
        Returns:
            Dictionary suitable for Kafka message payload
        """
        payload = self.to_dict(exclude_none=exclude_none, **kwargs)
        
        # Add Kafka-specific metadata
        kafka_meta = {
            'kafka_timestamp': datetime.now(timezone.utc).isoformat(),
            'message_version': '1.0',
            'processing_info': {
                'retry_count': self.retry_count,
                'max_retries': self.max_retries,
                'should_retry': self.retry_count < self.max_retries
            }
        }
        
        # Merge with existing meta
        if 'kafka_metadata' not in payload['meta']:
            payload['meta']['kafka_metadata'] = kafka_meta
        else:
            payload['meta']['kafka_metadata'].update(kafka_meta)
            
        return payload

    def to_flat_dict(self, exclude_none: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Convert to flat dictionary structure for easier processing
        
        Args:
            exclude_none: Whether to exclude None values
            **kwargs: Additional arguments for to_dict method
            
        Returns:
            Flattened dictionary representation
        """
        base_dict = self.to_dict(exclude_none=exclude_none, **kwargs)
        
        # Flatten the structure for certain use cases
        flat_dict = {
            'message_id': base_dict['id'],
            'message_topic': base_dict['topic'],
            'message_type': base_dict['type'],
            'tenant_id': base_dict['tenant'],
            'user_id': base_dict['user'],
            'priority': base_dict['priority'],
            'timestamp': base_dict['timestamp'].isoformat() if isinstance(base_dict['timestamp'], datetime) else base_dict['timestamp'],
            'retry_info': {
                'current': base_dict['retry_count'],
                'max': base_dict['max_retries']
            },
            **base_dict['data'],
            'metadata': base_dict['meta']
        }
        
        return flat_dict

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
    severity: str = Field(default="info", description="Event severity level")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")

class BizDataSyncMessage(BaseMessage):
    """Data synchronization message schema"""
    sync_type: str = Field(..., description="Synchronization type")
    entity_type: str = Field(..., description="Entity type to sync")
    entity_ids: List[str] = Field(..., description="Entity IDs to sync")
    direction: str = Field(default="both", description="Sync direction: both, push, or pull")

