# foxmask/task/message/process_manager.py
import asyncio
import multiprocessing
import signal
import sys
import time
import os
from typing import Optional
import psutil
from foxmask.core.logger import logger

# 注意：这里需要导入您的消费者
from .consumers import task_consumer


class MessageProcessManager:
    """消息处理进程管理器"""
    
    def __init__(self):
        self.consumer_process: Optional[multiprocessing.Process] = None
        self.process_info = {
            'pid': None,
            'start_time': None,
            'status': 'stopped',
            'is_running': False
        }
    
    def start_consumer_process(self):
        """启动独立的消费者进程"""
        if self.consumer_process and self.consumer_process.is_alive():
            logger.warning("Consumer process is already running")
            return
        
        try:
            # 创建并启动消费者进程
            self.consumer_process = multiprocessing.Process(
                target=self._run_consumer_process,
                name="foxmask-kafka-consumer",
                daemon=True
            )
            self.consumer_process.start()
            
            self.process_info.update({
                'pid': self.consumer_process.pid,
                'start_time': time.time(),
                'status': 'running',
                'is_running': True
            })
            
            logger.info(f"Started Kafka consumer process with PID: {self.consumer_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start consumer process: {e}")
            self.process_info.update({
                'status': 'error',
                'is_running': False
            })
            return False
    
    def _run_consumer_process(self):
        """在独立进程中运行消费者"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down consumer process")
            sys.exit(0)
        
        # 设置信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 设置进程名称
        try:
            import setproctitle
            setproctitle.setproctitle("foxmask-kafka-consumer")
        except ImportError:
            pass
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            logger.info("Starting Kafka consumer in separate process...")
            loop.run_until_complete(self._run_consumer())
        except KeyboardInterrupt:
            logger.info("Consumer process interrupted by user")
        except Exception as e:
            logger.error(f"Consumer process error: {e}")
        finally:
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()
            logger.info("Consumer process stopped")
    
    async def _run_consumer(self):
        """运行消费者主循环"""
        try:
            # 初始化消费者
            await task_consumer.start_consumers()
            logger.info("Kafka consumers started successfully in separate process")
            
            # 保持进程运行
            while True:
                await asyncio.sleep(10)
                # 可以在这里添加健康检查或状态报告
                
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise
        finally:
            await task_consumer.stop_consumers()
    
    def stop_consumer_process(self):
        """停止消费者进程"""
        if not self.consumer_process:
            logger.warning("No consumer process is running")
            return True
        
        try:
            if self.consumer_process.is_alive():
                # 优雅终止进程
                process = psutil.Process(self.consumer_process.pid)
                process.terminate()
                
                # 等待进程结束
                try:
                    self.consumer_process.join(timeout=30)
                    if self.consumer_process.is_alive():
                        logger.warning("Force killing consumer process")
                        self.consumer_process.kill()
                        self.consumer_process.join()
                except Exception as e:
                    logger.error(f"Error waiting for process to terminate: {e}")
                
                logger.info("Consumer process stopped successfully")
            else:
                logger.info("Consumer process was not running")
            
            self.process_info.update({
                'pid': None,
                'status': 'stopped',
                'is_running': False
            })
            self.consumer_process = None
            return True
            
        except psutil.NoSuchProcess:
            logger.warning("Consumer process already terminated")
            self.process_info.update({
                'pid': None,
                'status': 'stopped', 
                'is_running': False
            })
            self.consumer_process = None
            return True
        except Exception as e:
            logger.error(f"Error stopping consumer process: {e}")
            return False
    
    def get_process_status(self) -> dict:
        """获取进程状态信息"""
        status = self.process_info.copy()
        
        if self.consumer_process and self.consumer_process.is_alive():
            try:
                process = psutil.Process(self.consumer_process.pid)
                status.update({
                    'memory_usage': process.memory_info().rss,
                    'cpu_percent': process.cpu_percent(),
                    'create_time': process.create_time(),
                    'is_running': True,
                    'status': 'running'
                })
            except psutil.NoSuchProcess:
                status.update({
                    'is_running': False,
                    'status': 'stopped'
                })
        else:
            status.update({
                'is_running': False,
                'status': 'stopped'
            })
        
        return status
    
    def restart_consumer_process(self):
        """重启消费者进程"""
        logger.info("Restarting consumer process...")
        self.stop_consumer_process()
        time.sleep(2)  # 等待进程完全停止
        return self.start_consumer_process()


# 全局进程管理器实例
process_manager = MessageProcessManager()