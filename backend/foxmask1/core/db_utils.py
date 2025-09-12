# foxmask/core/db_utils.py
from typing import Dict, Any, Optional
import logging
from contextlib import asynccontextmanager
from foxmask.core.mongo import mongo_connection

logger = logging.getLogger(__name__)

class DatabaseUtils:
    """数据库工具类"""
    
    async def check_connection(self) -> bool:
        """检查数据库连接状态"""
        try:
            if mongo_connection.is_connected:
                await mongo_connection.client.admin.command('ping')
                return True
            return False
        except Exception:
            return False

    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            if not mongo_connection.is_connected:
                await mongo_connection.connect()
            
            db = mongo_connection.database
            stats = await db.command("dbStats")
            return {
                "db": stats.get("db", "unknown"),
                "collections": stats.get("collections", 0),
                "objects": stats.get("objects", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "index_size": stats.get("indexSize", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    async def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            if not mongo_connection.is_connected:
                await mongo_connection.connect()
            
            info = await mongo_connection.client.server_info()
            return {
                "version": info.get("version", "unknown"),
                "host": info.get("host", "unknown"),
                "process": info.get("process", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return {}

    @asynccontextmanager
    async def transaction_session(self):
        """事务会话上下文管理器"""
        session = None
        try:
            if not mongo_connection.is_connected:
                await mongo_connection.connect()
            
            async with await mongo_connection.client.start_session() as session:
                async with session.start_transaction():
                    yield session
                    
        except Exception as e:
            logger.error(f"Transaction session error: {e}")
            raise
        finally:
            if session:
                await session.end_session()

    async def backup_database(self, backup_path: str) -> bool:
        """备份数据库（简化版）"""
        # 实际实现需要根据具体备份策略
        logger.info(f"Database backup initiated to: {backup_path}")
        return True

    async def restore_database(self, backup_path: str) -> bool:
        """恢复数据库（简化版）"""
        # 实际实现需要根据具体恢复策略
        logger.info(f"Database restore initiated from: {backup_path}")
        return True

# 全局数据库工具实例
db_utils = DatabaseUtils()

# 连接状态检查装饰器
def require_db_connection(func):
    """确保数据库连接已建立的装饰器"""
    async def wrapper(*args, **kwargs):
        if not mongo_connection.is_connected:
            await mongo_connection.connect()
        return await func(*args, **kwargs)
    return wrapper