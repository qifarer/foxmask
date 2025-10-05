#!/usr/bin/env python3
"""
知识库项目消息消费者启动脚本
"""

import asyncio
import signal
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from foxmask.core.message.consumers import task_consumer
from foxmask.core.logger import logger

async def main_async():
    """主异步函数"""
    logger.info("Starting Knowledge Item Consumer Service")
    
    try:
        # 运行消费者 - 使用 await 调用异步方法
        await task_consumer.start_consumers()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        raise

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown()))
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown()))
    
    try:
        # 运行异步主函数
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

async def shutdown():
    """优雅关闭"""
    logger.info("Shutting down...")
    await task_consumer.stop_consumers()
    sys.exit(0)

if __name__ == "__main__":
    main()