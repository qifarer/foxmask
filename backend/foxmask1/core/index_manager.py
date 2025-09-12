# foxmask/core/index_manager.py
import logging
from typing import Dict, Any
from foxmask.core.mongo import mongo_connection

logger = logging.getLogger(__name__)

class IndexManager:
    """数据库索引管理类"""
    
    async def create_all_indexes(self):
        """创建所有集合的索引"""
        try:
            if not mongo_connection.is_connected:
                await mongo_connection.connect()
            
            # 文件域索引
            await self._create_file_indexes()
            
            # 认证域索引
            await self._create_auth_indexes()
            
            # 标签域索引
            await self._create_tag_indexes()
            
            logger.info("All database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    async def _create_file_indexes(self):
        """创建文件域索引"""
        try:
            db = mongo_connection.database
            
            # 文件集合索引
            files = db["files"]
            await files.create_index("owner_id")
            await files.create_index("tenant_id")
            await files.create_index("is_deleted")
            await files.create_index("status")
            await files.create_index("created_at")
            await files.create_index([("file_type", 1), ("status", 1)])
            
            # 文本搜索索引
            try:
                await files.create_index([("filename", "text"), ("tags", "text")])
            except Exception as e:
                logger.warning(f"Text index creation failed: {e}")
            
            # 文件分块索引
            chunks = db["file_chunks"]
            await chunks.create_index([("file_id", 1), ("chunk_number", 1)], unique=True)
            
            # 访问日志索引
            access_logs = db["file_access_logs"]
            await access_logs.create_index([("file_id", 1), ("accessed_at", -1)])
            await access_logs.create_index("accessed_at", expireAfterSeconds=2592000)
            
            logger.debug("File domain indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create file indexes: {e}")

    async def _create_auth_indexes(self):
        """创建认证域索引"""
        try:
            db = mongo_connection.database
            
            # 用户集合索引
            users = db["users"]
            await users.create_index("email", unique=True)
            await users.create_index("username", unique=True)
            await users.create_index("is_active")
            
            logger.debug("Auth domain indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create auth indexes: {e}")

    async def _create_tag_indexes(self):
        """创建标签域索引"""
        try:
            db = mongo_connection.database
            
            # 标签集合索引
            tags = db["tags"]
            await tags.create_index("name", unique=True)
            await tags.create_index("category")
            
            logger.debug("Tag domain indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create tag indexes: {e}")

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            stats = {}
            db = mongo_connection.database
            
            collections = await db.list_collection_names()
            for collection_name in collections:
                collection = db[collection_name]
                indexes = await collection.index_information()
                stats[collection_name] = {
                    "index_count": len(indexes),
                    "indexes": list(indexes.keys())
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

# 全局索引管理器实例
index_manager = IndexManager()