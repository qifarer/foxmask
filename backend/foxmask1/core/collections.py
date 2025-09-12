# foxmask/core/collections.py
from typing import Dict, Any
import logging
from foxmask.core.mongo import mongo_connection

logger = logging.getLogger(__name__)

class CollectionManager:
    """集合访问管理类"""
    
    async def get_collection(self, collection_name: str):
        """获取指定集合"""
        if not mongo_connection.is_connected:
            await mongo_connection.connect()
        return mongo_connection.database[collection_name]

    async def get_file_collection(self):
        """获取文件集合"""
        return await self.get_collection("files")

    async def get_user_collection(self):
        """获取用户集合"""
        return await self.get_collection("users")

    async def get_tag_collection(self):
        """获取标签集合"""
        return await self.get_collection("tags")

    async def get_audit_collection(self):
        """获取审计日志集合"""
        return await self.get_collection("audit_logs")

    async def list_collections(self) -> Dict[str, Any]:
        """列出所有集合信息"""
        try:
            db = mongo_connection.database
            collections = await db.list_collection_names()
            
            result = {}
            for collection_name in collections:
                collection = db[collection_name]
                stats = await collection.estimated_document_count()
                result[collection_name] = {
                    "document_count": stats,
                    "is_capped": collection.options().get("capped", False)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return {}

# 全局集合管理器实例
collection_manager = CollectionManager()

# 便捷访问函数
async def get_collection(collection_name: str):
    return await collection_manager.get_collection(collection_name)

async def get_file_collection():
    return await collection_manager.get_file_collection()

async def get_user_collection():
    return await collection_manager.get_user_collection()