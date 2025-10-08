#!/usr/bin/env python3
"""
独立消息消费者进程启动脚本
可以直接运行此脚本启动消息处理，不依赖FastAPI主进程
"""
import asyncio
import signal
import sys
import logging
from pathlib import Path
from beanie.exceptions import CollectionWasNotInitialized

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from foxmask.task.message.consumers import task_consumer
from foxmask.core.logger import logger
from foxmask.core.mongo import connect_to_mongo, close_mongo_connection, mongodb
from foxmask.core.kafka import kafka_manager
from foxmask.task.message.kafka_topic import setup_kafka_topics
from foxmask.file.mongo import init_file_db
# from foxmask.file.api.routers import file_router, upload_router

from foxmask.knowledge.mongo import init_knowledge_db_with_client



class StandaloneConsumer:
    """独立消费者运行器"""

    def __init__(self):
        self.running = False
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def initialize_services(self):
        """初始化服务"""
        logger.info("Initializing services for standalone consumer...")

        # 连接MongoDB并初始化Beane模型
        await connect_to_mongo()
        logger.info("MongoDB (Beanie) initialized")

        file_db = init_file_db(motor_client=mongodb.client, database_name='foxmask')
        await file_db.init_file_db()

        await init_knowledge_db_with_client(mongodb.client)
        # 设置Kafka主题
        await setup_kafka_topics()
        logger.info("Kafka topics setup completed")

        logger.info("All services initialized successfully")

    async def cleanup_services(self):
        """清理服务"""
        logger.info("Cleaning up services...")
        await task_consumer.stop_consumers()
        await kafka_manager.close()
        await close_mongo_connection()
        logger.info("Services cleaned up successfully")

    async def run(self):
        """运行消费者"""
        self.running = True
        try:
            await self.initialize_services()

            logger.info("Starting standalone Kafka consumer...")
            await task_consumer.start_consumers()
            logger.info("Kafka consumer started successfully")

            while self.running:
                await asyncio.sleep(1)

        except CollectionWasNotInitialized:
            logger.error(
                "Beanie collection not initialized! "
                "Please verify all entity models are registered in connect_to_mongo()."
            )
            raise
        except Exception as e:
            logger.exception(f"Consumer runtime error: {e}")
            raise
        finally:
            logger.info("Shutting down Kafka consumer...")
            await self.cleanup_services()
            logger.info("Kafka consumer stopped")


async def main():
    """主函数"""
    consumer = StandaloneConsumer()
    try:
        await consumer.run()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
