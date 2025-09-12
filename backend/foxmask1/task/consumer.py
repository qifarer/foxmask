from core.kafka_client import KafkaConsumer
from core.config import settings
from .handlers import handle_knowledge_item_created, handle_knowledge_item_parsed, handle_knowledge_item_vectorized
import asyncio

class KnowledgeConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer()
    
    async def start_consuming(self):
        await self.consumer.init_consumer(
            group_id=settings.KAFKA_CONSUMER_GROUP,
            topics=["knowledge-item-created", "knowledge-item-parsed", "knowledge-item-vectorized"]
        )
        
        try:
            async for msg in self.consumer.consumer:
                try:
                    if msg.topic == "knowledge-item-created":
                        await handle_knowledge_item_created(msg.value)
                    elif msg.topic == "knowledge-item-parsed":
                        await handle_knowledge_item_parsed(msg.value)
                    elif msg.topic == "knowledge-item-vectorized":
                        await handle_knowledge_item_vectorized(msg.value)
                except Exception as e:
                    print(f"Error processing message: {e}")
        except asyncio.CancelledError:
            print("Consumer task cancelled")
        finally:
            await self.consumer.close()

# 全局消费者实例
knowledge_consumer = KnowledgeConsumer()