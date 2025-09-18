# -*- coding: utf-8 -*-
# foxmask/task/message/producers.py
# Kafka producers for various task messages

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from foxmask.core.kafka import kafka_manager, KafkaMessage
from .schemas import (
    MessageTopicEnum,
    MessagePriorityEnum,
    KnowledgeProcessingMessage,
    NotificationMessage,
    SystemEventMessage,
    BizDataSyncMessage
)
from foxmask.core.logger import logger
from foxmask.core.config import settings


class TaskProducer:
    """Kafka 任务生产者，生成特定主题的消息"""
    def __init__(self):
        self.message_serializer = {
            MessageTopicEnum.KB_PROCESSING: KnowledgeProcessingMessage,
            MessageTopicEnum.NOTIFICATIONS: NotificationMessage,
            MessageTopicEnum.SYSTEM_EVENTS: SystemEventMessage,
            MessageTopicEnum.BIZ_DATA_SYNC: BizDataSyncMessage
        }

    async def produce_knowledge_processing_task(
        self,
        message: KnowledgeProcessingMessage
    ) -> str:
        """生产知识处理任务消息"""
        try:
            message_id = await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING.value,
                value=message.model_dump(),  # 统一使用 model_dump()
                key=message.key  # 按 knowledge item ID 分区
            )
            logger.info(
                f"Knowledge processing task produced for item: {message.key}, "
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
        priority: MessagePriorityEnum = MessagePriorityEnum.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """生产通知消息"""
        try:
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=MessageTopicEnum.NOTIFICATIONS,
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
                topic=MessageTopicEnum.NOTIFICATIONS.value,  # 使用 enum 值
                value=notification.model_dump(),
                key=user_id  # 按 user ID 分区
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
        priority: MessagePriorityEnum = MessagePriorityEnum.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """生产系统事件消息"""
        try:
            event = SystemEventMessage(
                message_id=str(uuid.uuid4()),
                type=MessageTopicEnum.SYSTEM_EVENTS,
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
                topic=MessageTopicEnum.SYSTEM_EVENTS.value,  # 使用 enum 值
                value=event.model_dump(),
                key=component  # 按 component 分区
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
        priority: MessagePriorityEnum = MessagePriorityEnum.NORMAL,
        correlation_id: Optional[str] = None
    ) -> str:
        """生产数据同步消息"""
        try:
            sync = BizDataSyncMessage(
                message_id=str(uuid.uuid4()),
                type=MessageTopicEnum.BIZ_DATA_SYNC,
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
                topic=MessageTopicEnum.BIZ_DATA_SYNC.value,  # 使用 enum 值
                value=sync.model_dump(),
                key=entity_type  # 按 entity type 分区
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
        topic: MessageTopicEnum,
        key_field: Optional[str] = None
    ) -> List[str]:
        """批量生产消息"""
        message_ids = []
        for message_data in messages:
            try:
                message_type = message_data.get('type')
                if message_type not in self.message_serializer:
                    logger.warning(f"Unknown message type: {message_type}")
                    continue
                message_class = self.message_serializer[message_type]
                message = message_class(**message_data)
                key = str(message_data[key_field]) if key_field and key_field in message_data else None
                message_id = await kafka_manager.send_message(
                    topic=topic.value,  # 使用 enum 值
                    value=message.model_dump(),
                    key=key
                )
                message_ids.append(message_id)
            except Exception as e:
                logger.error(f"Failed to produce batch message: {e}")
                continue
        logger.info(f"Produced {len(message_ids)}/{len(messages)} batch messages to topic {topic.value}")
        return message_ids


# 全局任务生产者实例
task_producer = TaskProducer()