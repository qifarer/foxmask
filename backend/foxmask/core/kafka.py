from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaTimeoutError
from kafka.admin import KafkaAdminClient, NewTopic  # 仍然使用同步客户端进行管理操作
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List, AsyncGenerator
import uuid
from datetime import datetime
from functools import wraps
import logging

from .config import settings
from .logger import logger

def retry_kafka_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying Kafka operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (KafkaError, KafkaTimeoutError, Exception) as e:
                    last_exception = e
                    logger.warning(
                        f"Kafka operation failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
            logger.error(f"Kafka operation failed after {max_retries} attempts: {last_exception}")
            raise last_exception
        return wrapper
    return decorator

class KafkaMessage:
    """Kafka message wrapper with metadata"""
    
    def __init__(
        self, 
        topic: str, 
        value: Dict[str, Any], 
        key: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.topic = topic
        self.key = key
        self.value = value
        self.timestamp = timestamp or datetime.utcnow()
        self.headers = headers or {}
        
        # Add standard headers
        self.headers.update({
            'message_id': self.message_id,
            'timestamp': self.timestamp.isoformat(),
            'source': settings.APP_NAME
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            'message_id': self.message_id,
            'topic': self.topic,
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'headers': self.headers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaMessage':
        """Create message from dictionary"""
        return cls(
            topic=data['topic'],
            value=data['value'],
            key=data.get('key'),
            message_id=data.get('message_id'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            headers=data.get('headers', {})
        )

class AIOKafkaManager:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.admin_client: Optional[KafkaAdminClient] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.topics_created = set()
        self.running = False

    @retry_kafka_operation(max_retries=3, delay=1.0)
    async def create_producer(self):
        """Create AIOKafka producer with retry mechanism"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                compression_type='gzip',
                request_timeout_ms=30000,
                max_batch_size=16384,  # 16KB
                linger_ms=5,  # 5ms linger for batching
                retry_backoff_ms=100,
                security_protocol='PLAINTEXT'
            )
            await self.producer.start()
            logger.info("AIOKafka producer created successfully")
        except Exception as e:
            logger.error(f"Failed to create AIOKafka producer: {e}")
            raise

    async def create_topic(self, topic_name: str, num_partitions: int = 3, replication_factor: int = 1):
        """Create Kafka topic if it doesn't exist (using sync admin client)"""
        if topic_name in self.topics_created:
            return
            
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                client_id='foxmask-admin'
            )
            
            topic_list = [NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                topic_configs={
                    'retention.ms': '604800000',  # 7 days
                    'cleanup.policy': 'delete'
                }
            )]
            
            self.admin_client.create_topics(new_topics=topic_list, validate_only=False)
            self.topics_created.add(topic_name)
            logger.info(f"Kafka topic '{topic_name}' created successfully")
        except Exception as e:
            if "TopicAlreadyExistsError" in str(e) or "already exists" in str(e):
                logger.info(f"Kafka topic '{topic_name}' already exists")
                self.topics_created.add(topic_name)
            else:
                logger.error(f"Failed to create Kafka topic '{topic_name}': {e}")
                raise

    @retry_kafka_operation(max_retries=3, delay=1.0)
    async def send_message(self, topic: str, value: Dict[str, Any], key: Optional[str] = None) -> str:
        """Send message to Kafka topic with retry mechanism"""
        if not self.producer:
            await self.create_producer()
        
        # Ensure topic exists
        await self.create_topic(topic)
        
        # Create message with metadata
        message = KafkaMessage(topic, value, key)
        
        try:
            # Convert headers to list of tuples
            kafka_headers = [(k, v.encode()) for k, v in message.headers.items()]
            
            # Send message asynchronously
            await self.producer.send_and_wait(
                topic=topic,
                value=message.to_dict(),
                key=key,
                headers=kafka_headers
            )
            
            logger.info(
                f"Message {message.message_id} sent to topic '{topic}'"
            )
            
            return message.message_id
            
        except KafkaTimeoutError as e:
            logger.error(f"Kafka send timeout for message {message.message_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send message {message.message_id} to Kafka: {e}")
            raise

    async def send_messages_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Send batch of messages efficiently"""
        if not self.producer:
            await self.create_producer()
        
        message_ids = []
        
        for message_data in messages:
            try:
                message_id = await self.send_message(
                    topic=message_data['topic'],
                    value=message_data['value'],
                    key=message_data.get('key')
                )
                message_ids.append(message_id)
            except Exception as e:
                logger.error(f"Failed to send batch message: {e}")
                continue
        
        return message_ids

    async def create_consumer(
        self, 
        topic: str, 
        group_id: str,
        auto_offset_reset: str = 'earliest',
        enable_auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000
    ) -> AIOKafkaConsumer:
        """Create AIOKafka consumer"""
        try:
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=enable_auto_commit,
                auto_commit_interval_ms=auto_commit_interval_ms,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                max_poll_records=100,
                max_poll_interval_ms=300000,
                session_timeout_ms=45000,
                heartbeat_interval_ms=15000
            )
            
            await consumer.start()
            self.consumers[group_id] = consumer
            logger.info(f"AIOKafka consumer created for topic '{topic}' with group ID '{group_id}'")
            return consumer
            
        except Exception as e:
            logger.error(f"Failed to create AIOKafka consumer: {e}")
            raise

    async def consume_messages(
        self,
        topic: str,
        group_id: str,
        processor: Callable[[Dict[str, Any]], Any],
        batch_size: int = 100,
        timeout_ms: int = 1000
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Consume messages from Kafka topic and yield them for processing"""
        consumer = await self.create_consumer(topic, group_id)
        
        try:
            while self.running:
                try:
                    # Get messages asynchronously
                    async for message in consumer:
                        if not self.running:
                            break
                            
                        try:
                            yield message
                            # Auto-commit is handled by the consumer
                            
                        except Exception as e:
                            logger.error(f"Error processing message {message.value.get('message_id')}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error in consumer for group {group_id}: {e}")
                    await asyncio.sleep(1)  # Wait before retrying
                    
        finally:
            await consumer.stop()
            if group_id in self.consumers:
                del self.consumers[group_id]

    async def get_consumer_position(self, group_id: str, topic: str) -> Optional[Dict[str, Any]]:
        """Get consumer position information"""
        if group_id not in self.consumers:
            return None
        
        consumer = self.consumers[group_id]
        
        try:
            assignment = consumer.assignment()
            positions = {}
            
            for partition in assignment:
                position = await consumer.position(partition)
                positions[str(partition)] = position
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting consumer position for group {group_id}: {e}")
            return None

    async def close(self):
        """Close all Kafka connections"""
        self.running = False
        
        # Close producer
        if self.producer:
            await self.producer.stop()
            logger.info("AIOKafka producer closed")
        
        # Close consumers
        for group_id, consumer in list(self.consumers.items()):
            try:
                await consumer.stop()
                logger.info(f"AIOKafka consumer for group {group_id} closed")
            except Exception as e:
                logger.error(f"Error closing consumer {group_id}: {e}")
        
        # Close admin client
        if self.admin_client:
            self.admin_client.close()
            logger.info("Kafka admin client closed")
        
        logger.info("All AIOKafka connections closed")

# Global AIOKafka manager instance
kafka_manager = AIOKafkaManager()