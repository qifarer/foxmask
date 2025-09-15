# -*- coding: utf-8 -*-
# foxmask/task/producers.py
# Kafka producers for various task messages

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from foxmask.core.kafka import kafka_manager, KafkaMessage
from .schemas import (
    KnowledgeProcessingMessage, FileProcessingMessage,
    NotificationMessage, SystemEventMessage, DataSyncMessage,
    MessageType, MessagePriority
)
from foxmask.core.logger import logger
from foxmask.core.config import settings

class TaskProducer:
    def __init__(self):
        self.message_serializer = {
            MessageType.KNOWLEDGE_PROCESSING: KnowledgeProcessingMessage,
            MessageType.FILE_PROCESSING: FileProcessingMessage,
            MessageType.NOTIFICATION: NotificationMessage,
            MessageType.SYSTEM_EVENT: SystemEventMessage,
            MessageType.DATA_SYNC: DataSyncMessage
        }
    
    async def produce_file_processing_task(
        self,
        file_id: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """Produce file processing task message with enhanced options"""
        try:
            # Validate processing type
            valid_processing_types = ["create_item", "transcode", "metadata_extraction"]
            if processing_type not in valid_processing_types:
                raise ValueError(f"Invalid processing type: {processing_type}")
            
            message = FileProcessingMessage(
                message_id=str(uuid.uuid4()),   
                type=MessageType.FILE_PROCESSING,
                priority=priority,
                source=settings.APP_NAME,
                correlation_id=correlation_id,
                metadata={},
                file_id=file_id,
                processing_type=processing_type,
                options=options or {}
            )
            
            message_id = await kafka_manager.send_message(
                topic="file_processing",
                value=message.model_dump(),
                key=file_id  # Partition by file ID
            )
            
            logger.info(
                f"File processing task produced for file: {file_id}, "
                f"type: {processing_type}, message ID: {message_id}"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to produce file processing task: {e}")
            raise

    async def produce_knowledge_processing_task(
        self,
        knowledge_item_id: str,
        process_types: List[str],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Produce knowledge processing task message"""
        try:
            message = KnowledgeProcessingMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.KNOWLEDGE_PROCESSING,
                priority=priority,
                source=settings.APP_NAME,
                correlation_id=correlation_id,
                metadata=metadata or {},
                knowledge_item_id=knowledge_item_id,
                process_types=process_types
            )
            
            message_id = await kafka_manager.send_message(
                topic=settings.KAFKA_KNOWLEDGE_TOPIC,
                value=message.model_dump(),
                key=knowledge_item_id  # Partition by knowledge item ID
            )
            
            logger.info(
                f"Knowledge processing task produced for item: {knowledge_item_id}, "
                f"message ID: {message_id}"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to produce knowledge processing task: {e}")
            raise

    

    async def produce_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """Produce notification message"""
        try:
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.NOTIFICATION,
                priority=priority,
                source=settings.APP_NAME,
                correlation_id=correlation_id,
                metadata={},
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {}
            )
            
            message_id = await kafka_manager.send_message(
                topic="notifications",
                value=notification.model_dump(),
                key=user_id  # Partition by user ID
            )
            
            logger.info(
                f"Notification produced for user: {user_id}, "
                f"message ID: {message_id}"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to produce notification: {e}")
            raise

    async def produce_system_event(
        self,
        event_type: str,
        component: str,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """Produce system event message"""
        try:
            event = SystemEventMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.SYSTEM_EVENT,
                priority=priority,
                source=settings.APP_NAME,
                correlation_id=correlation_id,
                metadata={},
                event_type=event_type,
                component=component,
                severity=severity,
                details=details or {}
            )
            
            message_id = await kafka_manager.send_message(
                topic="system_events",
                value=event.model_dump(),
                key=component  # Partition by component
            )
            
            logger.info(
                f"System event produced: {event_type}, "
                f"component: {component}, message ID: {message_id}"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to produce system event: {e}")
            raise

    async def produce_data_sync(
        self,
        sync_type: str,
        entity_type: str,
        entity_ids: List[str],
        direction: str = "both",
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """Produce data synchronization message"""
        try:
            sync = DataSyncMessage(
                message_id=str(uuid.uuid4()),
                type=MessageType.DATA_SYNC,
                priority=priority,
                source=settings.APP_NAME,
                correlation_id=correlation_id,
                metadata={},
                sync_type=sync_type,
                entity_type=entity_type,
                entity_ids=entity_ids,
                direction=direction
            )
            
            message_id = await kafka_manager.send_message(
                topic="data_sync",
                value=sync.model_dump(),
                key=entity_type  # Partition by entity type
            )
            
            logger.info(
                f"Data sync produced: {sync_type}, "
                f"entity type: {entity_type}, message ID: {message_id}"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to produce data sync: {e}")
            raise

    async def produce_batch_messages(
        self,
        messages: List[Dict[str, Any]],
        topic: str,
        key_field: Optional[str] = None
    ) -> List[str]:
        """Produce batch of messages"""
        message_ids = []
        
        for message_data in messages:
            try:
                # Determine message type and validate
                message_type = message_data.get('type')
                if message_type not in self.message_serializer:
                    logger.warning(f"Unknown message type: {message_type}")
                    continue
                
                # Validate message schema
                message_class = self.message_serializer[message_type]
                message = message_class(**message_data)
                
                # Determine message key
                key = None
                if key_field and key_field in message_data:
                    key = str(message_data[key_field])
                
                message_id = await kafka_manager.send_message(
                    topic=topic,
                    value=message.model_dump(),
                    key=key
                )
                
                message_ids.append(message_id)
                
            except Exception as e:
                logger.error(f"Failed to produce batch message: {e}")
                continue
        
        logger.info(f"Produced {len(message_ids)}/{len(messages)} batch messages")
        return message_ids

# Global task producer instance
task_producer = TaskProducer()