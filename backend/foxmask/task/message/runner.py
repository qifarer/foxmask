# -*- coding: utf-8 -*-
# 独立 Kafka 消费进程入口
import asyncio
import signal
from foxmask.core.logger import logger
from foxmask.core.mongo import connect_to_mongo, close_mongo_connection
from foxmask.core.kafka import kafka_manager
from foxmask.task.message.consumers import task_consumer
from foxmask.task.message.kafka_topic import setup_kafka_topics


async def main():
    logger.info("🚀 Starting Kafka consumer process...")

    # 初始化 MongoDB 和 Kafka
    await connect_to_mongo()
    await setup_kafka_topics()
    await kafka_manager.create_producer()

    # 启动消费者
    await task_consumer.start_consumers()

    # 捕获信号，优雅关闭
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_stop():
        logger.info("🛑 Received stop signal, stopping consumers...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_stop)

    await stop_event.wait()

    # 停止消费者与连接
    await task_consumer.stop_consumers()
    await kafka_manager.close()
    await close_mongo_connection()
    logger.info("✅ Kafka consumer process stopped cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
