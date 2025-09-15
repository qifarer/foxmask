from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaTimeoutError
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import json
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, Callable, List, AsyncGenerator
import uuid
from functools import wraps

from .config import settings
from .logger import logger

def custom_json_serializer(obj):
    """自定义 JSON 序列化器，处理 datetime 和其他非标准类型"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

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
        timestamp = data.get('timestamp')
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            topic=data['topic'],
            value=data['value'],
            key=data.get('key'),
            message_id=data.get('message_id'),
            timestamp=timestamp,
            headers=data.get('headers', {})
        )

class KafkaService:
    """Kafka服务，提供Topic创建、消息生产和消费功能"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.admin_client: Optional[KafkaAdminClient] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.topics_created = set()
        self.running = False

    @retry_kafka_operation(max_retries=3, delay=1.0)
    async def create_producer(self):
        """创建Kafka生产者"""
        try:
            if self.producer and not self.producer._closed:
                return
                
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda v: json.dumps(v, default=custom_json_serializer).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                compression_type='gzip',
                request_timeout_ms=30000,
                max_batch_size=16384,
                linger_ms=5,
                retry_backoff_ms=100,
                security_protocol='PLAINTEXT'
            )
            await self.producer.start()
            logger.info("Kafka producer created successfully")
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise    

    async def create_topic(
        self, 
        topic_name: str, 
        num_partitions: int = 3, 
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None
    ):
        """创建Kafka Topic"""
        if topic_name in self.topics_created:
            return
            
        try:
            if not self.admin_client:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                    client_id=f'{settings.APP_NAME}-admin'
                )
            
            # 检查Topic是否已存在
            existing_topics = self.admin_client.list_topics()
            if topic_name in existing_topics:
                self.topics_created.add(topic_name)
                logger.info(f"Kafka topic '{topic_name}' already exists")
                return
            
            # 创建Topic配置
            topic_config = config or {
                'retention.ms': '604800000',  # 7 days
                'cleanup.policy': 'delete'
            }
            
            # 创建Topic
            topic_list = [NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                topic_configs=topic_config
            )]
            
            self.admin_client.create_topics(new_topics=topic_list, validate_only=False)
            self.topics_created.add(topic_name)
            logger.info(f"Kafka topic '{topic_name}' created successfully")
            
        except TopicAlreadyExistsError:
            self.topics_created.add(topic_name)
            logger.info(f"Kafka topic '{topic_name}' already exists")
        except Exception as e:
            if "already exists" in str(e).lower():
                self.topics_created.add(topic_name)
                logger.info(f"Kafka topic '{topic_name}' already exists")
            else:
                logger.error(f"Failed to create Kafka topic '{topic_name}': {e}")
                raise

    async def ensure_topic_exists(self, topic_name: str) -> bool:
        """确保Topic存在"""
        try:
            if topic_name in self.topics_created:
                return True
                
            if not self.admin_client:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                    client_id=f'{settings.APP_NAME}-admin'
                )
            
            # 检查Topic是否已存在
            existing_topics = self.admin_client.list_topics()
            if topic_name in existing_topics:
                self.topics_created.add(topic_name)
                return True
            
            # 如果Topic不存在，则创建
            await self.create_topic(topic_name)
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring topic '{topic_name}' exists: {e}")
            return False


    @retry_kafka_operation(max_retries=3, delay=1.0)
    async def send_message(self, topic: str, value: Dict[str, Any], key: Optional[str] = None) -> str:
        """发送消息到Kafka Topic"""
        if not self.producer:
            await self.create_producer()
        
        # 确保Topic存在
        await self.ensure_topic_exists(topic)
        
        # 创建消息
        message = KafkaMessage(topic, value, key)
        
        
        try:
            # 转换headers为Kafka格式
            kafka_headers = [(k, str(v).encode('utf-8')) for k, v in message.headers.items()]
            
            # 发送消息
            await self.producer.send_and_wait(
                topic=topic,
                value=message.to_dict(),
                key=key,
                headers=kafka_headers
            )
            
            logger.info(f"Message {message.message_id} sent to topic '{topic}'")
            return message.message_id
            
        except KafkaTimeoutError as e:
            logger.error(f"Kafka send timeout for message {message.message_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send message {message.message_id} to Kafka: {e}")
            raise

    async def send_messages_batch(self, messages: List[Dict[str, Any]]) -> List[str]:
        """批量发送消息"""
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
        """创建Kafka消费者"""
        try:
            # 确保Topic存在
            await self.ensure_topic_exists(topic)
            
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=enable_auto_commit,
                auto_commit_interval_ms=auto_commit_interval_ms,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                max_poll_records=100,
                max_poll_interval_ms=300000,
                session_timeout_ms=45000,
                heartbeat_interval_ms=15000
            )
            
            await consumer.start()
            self.consumers[group_id] = consumer
            logger.info(f"Kafka consumer created for topic '{topic}' with group ID '{group_id}'")
            return consumer
            
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise

    async def subscribe_to_topic(self, topic: str, group_id: str) -> bool:
        """订阅Kafka Topic"""
        try:
            if group_id in self.consumers:
                logger.info(f"Already subscribed to topic '{topic}' with group ID '{group_id}'")
                return True
                
            await self.create_consumer(topic, group_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topic '{topic}': {e}")
            return False

    async def consume_messages(
        self,
        topic: str,
        group_id: str,
        processor: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """消费消息"""
        # 确保已订阅Topic
        if not await self.subscribe_to_topic(topic, group_id):
            raise Exception(f"Failed to subscribe to topic '{topic}'")
        
        consumer = self.consumers[group_id]
        
        try:
            self.running = True
            while self.running:
                try:
                    async for message in consumer:
                        if not self.running:
                            break
                            
                        try:
                            # 解析消息
                            message_value = message.value
                            if isinstance(message_value, dict) and 'value' in message_value:
                                # 提取实际的消息内容
                                yield message_value['value']
                                
                                # 如果有处理器，则调用处理器
                                if processor:
                                    await processor(message_value['value'])
                            else:
                                # 直接返回消息值
                                yield message_value
                                
                                # 如果有处理器，则调用处理器
                                if processor:
                                    await processor(message_value)
                                
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error in consumer for group {group_id}: {e}")
                    await asyncio.sleep(1)  # 等待后重试
                    
        finally:
            await consumer.stop()
            if group_id in self.consumers:
                del self.consumers[group_id]

    async def get_consumer_position(self, group_id: str, topic: str) -> Optional[Dict[str, Any]]:
        """获取消费者位置信息"""
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

    async def list_topics(self) -> List[str]:
        """列出所有Topic"""
        try:
            if not self.admin_client:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                    client_id=f'{settings.APP_NAME}-admin'
                )
            
            return list(self.admin_client.list_topics())
        except Exception as e:
            logger.error(f"Failed to list topics: {e}")
            return []

    async def get_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """获取Topic信息"""
        try:
            if not self.admin_client:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                    client_id=f'{settings.APP_NAME}-admin'
                )
            
            # 获取Topic描述
            from kafka.admin import ConfigResource, ConfigResourceType
            resource = ConfigResource(ConfigResourceType.TOPIC, topic)
            configs = self.admin_client.describe_configs([resource])
            
            # 获取分区信息
            cluster_metadata = self.admin_client.describe_topics([topic])
            
            return {
                'config': {config[0]: config[1] for config in configs[resource].items()},
                'partitions': cluster_metadata[topic].partitions
            }
        except Exception as e:
            logger.error(f"Failed to get info for topic '{topic}': {e}")
            return None

    async def close(self):
        """关闭所有Kafka连接"""
        self.running = False
        
        # 关闭生产者
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")
        
        # 关闭消费者
        for group_id, consumer in list(self.consumers.items()):
            try:
                await consumer.stop()
                logger.info(f"Kafka consumer for group {group_id} closed")
            except Exception as e:
                logger.error(f"Error closing consumer {group_id}: {e}")
        
        # 关闭Admin客户端
        if self.admin_client:
            try:
                self.admin_client.close()
                logger.info("Kafka admin client closed")
            except Exception as e:
                logger.error(f"Error closing admin client: {e}")
        
        logger.info("All Kafka connections closed")

# 全局Kafka服务实例
kafka_manager = KafkaService()