# -*- coding: utf-8 -*-
# foxmask/task/consumers.py
# AIOKafka consumers for various task messages

import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from foxmask.core.kafka import kafka_manager
from foxmask.core.logger import logger
from foxmask.core.config import settings
from foxmask.core.schemas import (
    KnowledgeProcessingMessage, FileProcessingMessage,
    NotificationMessage, SystemEventMessage, DataSyncMessage
)

from foxmask.knowledge.services.knowledge_processing import knowledge_processing_service
from foxmask.file.services import file_service
from foxmask.task.services import task_service
from foxmask.task.dead_letter_processor import dead_letter_processor
from foxmask.tag.services import tag_service


class AIOTaskConsumer:
    def __init__(self):
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.processors: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            settings.KAFKA_KNOWLEDGE_TOPIC: self.process_knowledge_message,
            "file_processing": self.process_file_message,
            "notifications": self.process_notification_message,
            "system_events": self.process_system_event_message,
            "data_sync": self.process_data_sync_message
        }
        self.running = False
        self.consumer_tasks = []

    async def start_consumers(self):
        """Start all AIOKafka consumers"""
        self.running = True
        
        # Start consumer for each topic
        for topic, processor in self.processors.items():
            task = asyncio.create_task(
                self.consume_topic_messages(topic, f"{topic}_group", processor)
            )
            self.consumer_tasks.append(task)
        
        logger.info("All AIOKafka consumers started")

    async def stop_consumers(self):
        """Stop all AIOKafka consumers"""
        self.running = False
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        
        # Close all consumer connections
        for group_id, consumer in self.consumers.items():
            try:
                await consumer.stop()
                logger.info(f"AIOKafka consumer for group {group_id} closed")
            except Exception as e:
                logger.error(f"Error closing consumer {group_id}: {e}")
        
        self.consumers.clear()
        self.consumer_tasks.clear()
        
        logger.info("All AIOKafka consumers stopped")

    async def consume_topic_messages(self, topic: str, group_id: str, processor: Callable):
        """Consume messages from a specific topic using async generator"""
        try:
            logger.info(f"Starting to consume messages from topic: {topic}")
            
            async for message in kafka_manager.consume_messages(topic, group_id, processor):
                if not self.running:
                    break
                    
                try:
                    # Process the message
                    await processor(message.value)
                    
                    logger.debug(
                        f"Successfully processed message {message.value.get('message_id')} "
                        f"from topic {topic}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error processing message {message.value.get('message_id')} "
                        f"from topic {topic}: {e}"
                    )
                    
                    # Send to dead letter queue
                    await dead_letter_processor.send_to_dlq(
                        original_message=message.value,
                        failure_reason=str(e),
                        exception=e
                    )
                    
        except asyncio.CancelledError:
            logger.info(f"Consumer for topic {topic} was cancelled")
        except Exception as e:
            logger.error(f"Error in consumer for topic {topic}: {e}")
        finally:
            logger.info(f"Stopped consuming messages from topic: {topic}")

    async def process_knowledge_message(self, message_data: Dict[str, Any]):
        """Process knowledge processing message"""
        try:
            # Validate message schema
            message = KnowledgeProcessingMessage(**message_data)
            
            logger.info(
                f"Processing knowledge message {message.message_id} "
                f"for item {message.knowledge_item_id}"
            )
            
            # Process the knowledge item
            await knowledge_processing_service.process_knowledge_item({
                "knowledge_item_id": message.knowledge_item_id,
                "process_types": message.process_types,
                "retry_count": message.retry_count,
                "max_retries": message.max_retries
            })
            
            logger.info(
                f"Successfully processed knowledge message {message.message_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing knowledge message {message_data.get('message_id')}: {e}")
            raise

    async def process_file_message(self, message_data: Dict[str, Any]):
        """Process file processing message"""
        try:
            # Validate message schema
            message = FileProcessingMessage(**message_data)
            
            logger.info(
                f"Processing file message {message.message_id} "
                f"for file {message.file_id}"
            )
            
            # Process the file based on processing type
            processing_handlers = {
                "thumbnail": file_service.generate_thumbnail,
                "extract_text": file_service.extract_text,
                "validate": file_service.validate_file,
                "virus_scan": file_service.scan_for_viruses
            }
            
            handler = processing_handlers.get(message.processing_type)
            if handler:
                await handler(message.file_id, message.options)
            else:
                logger.warning(f"Unknown file processing type: {message.processing_type}")
            
            logger.info(
                f"Successfully processed file message {message.message_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing file message {message_data.get('message_id')}: {e}")
            raise

    async def process_notification_message(self, message_data: Dict[str, Any]):
        """Process notification message"""
        try:
            # Validate message schema
            message = NotificationMessage(**message_data)
            
            logger.info(
                f"Processing notification message {message.message_id} "
                f"for user {message.user_id}"
            )
            
            # TODO: Implement notification service integration
            # await notification_service.send(
            #     user_id=message.user_id,
            #     notification_type=message.notification_type,
            #     title=message.title,
            #     content=message.message,
            #     data=message.data
            # )
            
            logger.info(
                f"Successfully processed notification message {message.message_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing notification message {message_data.get('message_id')}: {e}")
            raise

    async def process_system_event_message(self, message_data: Dict[str, Any]):
        """Process system event message"""
        try:
            # Validate message schema
            message = SystemEventMessage(**message_data)
            
            logger.info(
                f"Processing system event message {message.message_id}: "
                f"{message.event_type} from {message.component}"
            )
            
            # TODO: Implement system event handling
            # await monitoring_service.record_event(
            #     event_type=message.event_type,
            #     component=message.component,
            #     severity=message.severity,
            #     details=message.details
            # )
            
            logger.info(
                f"Successfully processed system event message {message.message_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing system event message {message_data.get('message_id')}: {e}")
            raise

    async def process_data_sync_message(self, message_data: Dict[str, Any]):
        """Process data synchronization message"""
        try:
            # Validate message schema
            message = DataSyncMessage(**message_data)
            
            logger.info(
                f"Processing data sync message {message.message_id}: "
                f"{message.sync_type} for {message.entity_type}"
            )
            
            # TODO: Implement data synchronization
            # await sync_service.synchronize(
            #     entity_type=message.entity_type,
            #     entity_ids=message.entity_ids,
            #     direction=message.direction
            # )
            
            logger.info(
                f"Successfully processed data sync message {message.message_id}"
            )
            
        except Exception as e:
            logger.error(f"Error processing data sync message {message_data.get('message_id')}: {e}")
            raise

    async def get_consumer_stats(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get consumer statistics"""
        if group_id not in self.consumers:
            return None
        
        consumer = self.consumers[group_id]
        
        try:
            positions = await kafka_manager.get_consumer_position(group_id, consumer._subscription)
            
            stats = {
                'group_id': group_id,
                'assigned_partitions': list(positions.keys()),
                'positions': positions,
                'consumer_lag': {}  # Would need to get committed offsets from admin client
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting consumer stats for group {group_id}: {e}")
            return None

    async def pause_consumption(self, group_id: str):
        """Pause message consumption for a consumer group"""
        if group_id in self.consumers:
            consumer = self.consumers[group_id]
            consumer.pause()
            logger.info(f"Paused consumption for group {group_id}")

    async def resume_consumption(self, group_id: str):
        """Resume message consumption for a consumer group"""
        if group_id in self.consumers:
            consumer = self.consumers[group_id]
            consumer.resume()
            logger.info(f"Resumed consumption for group {group_id}")

# Global AIOKafka task consumer instance
task_consumer = AIOTaskConsumer()