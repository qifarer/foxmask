# foxmask/core/kafka.py

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
from foxmask.core.config import get_settings

settings = get_settings()

class KafkaProducer:
    def __init__(self):
        self.producer = None
    
    async def init_producer(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
    
    async def send_message(self, topic: str, message: dict):
        if self.producer:
            await self.producer.send_and_wait(topic, message)
    
    async def close(self):
        if self.producer:
            await self.producer.stop()

class KafkaConsumer:
    def __init__(self):
        self.consumer = None
    
    async def init_consumer(self, group_id: str, topics: list):
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
    
    async def close(self):
        if self.consumer:
            await self.consumer.stop()

# 全局Kafka生产者实例
kafka_producer = KafkaProducer()