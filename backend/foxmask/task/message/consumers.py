# -*- coding: utf-8 -*-
# foxmask/task/message/consumers.py
# Kafka task consumer with idempotent processing

import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from foxmask.core.mongo import mongodb
from foxmask.core.kafka import kafka_manager
from foxmask.core.logger import logger
from foxmask.core.config import settings
from .schemas import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    KnowledgeProcessingMessage,
    NotificationMessage,
    SystemEventMessage,
    BizDataSyncMessage
)
from foxmask.knowledge.services import knowledge_processing_service
from foxmask.file.services import file_service
from foxmask.task.services import task_service
from .dead_letter_processor import dead_letter_processor
from foxmask.tag.services import tag_service


class AIOTaskConsumer:
    """Kafka 任务消费者，处理特定主题的消息"""
    def __init__(self):
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.processors: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            MessageTopicEnum.KB_PROCESSING: self.process_knowledge_message,
            MessageTopicEnum.NOTIFICATIONS: self.process_notification_message,
            MessageTopicEnum.SYSTEM_EVENTS: self.process_system_event_message,
            MessageTopicEnum.BIZ_DATA_SYNC: self.process_bizdata_sync_message
        }
        self.running = False
        self.consumer_tasks: List[asyncio.Task] = []
     
    def wrap_idempotent_processor(
        self,
        processor: Callable[[Dict[str, Any]], Any],
        topic: str,
        collection: AsyncIOMotorCollection
    ) -> Callable[[Dict[str, Any], Optional[AIOKafkaConsumer]], Any]:
        """包装处理器，添加幂等性检查、偏移提交和 DLQ 处理"""
        async def wrapped_processor(message_data: Dict[str, Any], consumer: Optional[AIOKafkaConsumer] = None):
            message_id = message_data.get("message_id", "")
            if not message_id:
                logger.error(f"Invalid message in topic {topic}: {str(message_data)}")
                return
            if await collection.find_one({"message_id": message_id}):
                logger.info(f"Message {message_id} already processed in topic {topic}, skipping")
                if consumer:
                    await consumer.commit()
                return
            try:
                await processor(message_data)
                await collection.insert_one({
                    "message_id": message_id,
                    "processed_at": datetime.utcnow(),
                    "topic": topic
                })
                if consumer:
                    await consumer.commit()
                logger.info(f"Successfully processed message {message_id} in topic {topic}")
            except Exception as e:
                logger.error(f"Error processing message {message_id} in topic {topic}: {e}")
                await dead_letter_processor.send_to_dlq(
                    original_message=message_data,
                    failure_reason=str(e),
                    exception=e
                )
        return wrapped_processor
    
    async def consume_topic(self, topic: str, group_id: str, processor: Callable[[Dict[str, Any], Optional[AIOKafkaConsumer]], Any]):
        """将异步生成器转换为协程以处理消息"""
        try:
            async for message in kafka_manager.consume_messages(topic, group_id, processor):
                pass  # 消息已由 processor 处理
        except Exception as e:
            logger.error(f"Error consuming topic {topic} for group {group_id}: {e}")
            raise

    async def start_consumers(self):
        """启动所有 Kafka 消费者"""
        self.running = True
        # 初始化 MongoDB 客户端
        try:
            processed_collection = mongodb.database.processed_messages
            await processed_collection.create_index("message_id", unique=True)
            await processed_collection.create_index("processed_at", expireAfterSeconds=604800)
            logger.info("MongoDB connection initialized and indexes created")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise
        
        for topic, processor in self.processors.items():
            wrapped_processor = self.wrap_idempotent_processor(processor, topic, processed_collection)
            task = asyncio.create_task(
                self.consume_topic(topic.value, f"{topic.value}_group", wrapped_processor)
            )
            self.consumer_tasks.append(task)
            logger.info(f"Started consumer task for topic {topic}")
        logger.info("All Kafka consumers started")

    async def stop_consumers(self):
        """停止所有 Kafka 消费者"""
        self.running = False
        for task in self.consumer_tasks:
            task.cancel()
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        for group_id, consumer in list(self.consumers.items()):
            try:
                await consumer.commit()
                await consumer.stop()
                logger.info(f"Kafka consumer for group {group_id} closed")
            except Exception as e:
                logger.error(f"Error closing consumer {group_id}: {e}")
        self.consumers.clear()
        self.consumer_tasks.clear()
        logger.info("All Kafka consumers stopped")

    async def process_knowledge_message(self, message_data: Dict[str, Any]):
        """处理知识处理消息"""
        message_id = message_data.get("message_id", "")
        logger.info(f"Processing knowledge message: {message_id}")
        await knowledge_processing_service.process_knowledge(message_data)

    async def process_notification_message(self, message_data: Dict[str, Any]):
        """处理通知消息"""
        message = NotificationMessage(**message_data)
        logger.info(f"Processing notification message {message.message_id} for user {message.user_id}")
        # TODO: Implement notification service integration
        # await notification_service.send(
        #     user_id=message.user_id,
        #     notification_type=message.notification_type,
        #     title=message.title,
        #     content=message.message,
        #     data=message.data
        # )

    async def process_system_event_message(self, message_data: Dict[str, Any]):
        """处理系统事件消息"""
        message = SystemEventMessage(**message_data)
        logger.info(f"Processing system event message {message.message_id}: {message.event_type} from {message.component}")
        # TODO: Implement system event handling
        # await monitoring_service.record_event(
        #     event_type=message.event_type,
        #     component=message.component,
        #     severity=message.severity,
        #     details=message.details
        # )

    async def process_bizdata_sync_message(self, message_data: Dict[str, Any]):
        """处理数据同步消息"""
        message = BizDataSyncMessage(**message_data)
        logger.info(f"Processing data sync message {message.message_id}: {message.sync_type} for {message.entity_type}")
        # TODO: Implement data synchronization
        # await sync_service.synchronize(
        #     entity_type=message.entity_type,
        #     entity_ids=message.entity_ids,
        #     direction=message.direction
        # )

    async def get_consumer_stats(self, group_id: str) -> Optional[Dict[str, Any]]:
        """获取消费者统计信息"""
        if group_id not in self.consumers:
            logger.warning(f"No consumer found for group {group_id}")
            return None
        try:
            consumer = self.consumers[group_id]
            positions = await kafka_manager.get_consumer_position(group_id, consumer._subscription)
            return {
                'group_id': group_id,
                'assigned_partitions': list(positions.keys()),
                'positions': positions,
                'consumer_lag': {}  # TODO: Implement lag calculation
            }
        except Exception as e:
            logger.error(f"Error getting consumer stats for group {group_id}: {e}")
            return None

    async def pause_consumption(self, group_id: str):
        """暂停消费者组的消息消费"""
        if group_id in self.consumers:
            self.consumers[group_id].pause()
            logger.info(f"Paused consumption for group {group_id}")

    async def resume_consumption(self, group_id: str):
        """恢复消费者组的消息消费"""
        if group_id in self.consumers:
            self.consumers[group_id].resume()
            logger.info(f"Resumed consumption for group {group_id}")


# 全局 Kafka 任务消费者实例
task_consumer = AIOTaskConsumer()