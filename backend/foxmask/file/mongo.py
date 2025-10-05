from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie
import logging
from bson import ObjectId
from .models import UploadTask, UploadTaskFile, UploadTaskFileChunk, File, FileLog
        
logger = logging.getLogger(__name__)

class FileDatabase:
    """文件数据库管理器 - 支持 Beanie 2.0.0"""
    
    def __init__(self, motor_client: AsyncIOMotorClient, database_name: str):
        self.motor_client = motor_client
        self.database_name = database_name
        self.db = motor_client[database_name]
        self._initialized = False
    
    async def init_file_db(self):
        """初始化文件数据库 - Beanie 2.0.0 版本"""
        if self._initialized:
            return
        
        try:
            logger.info(f"Initializing file database: {self.database_name}")
            
            # 导入所有模型
            document_models = [
                File, FileLog,  # 文件管理模型
                UploadTask, UploadTaskFile, UploadTaskFileChunk  # 上传任务模型
            ]
            
            # Beanie 2.0.0 初始化 - 会自动创建模型中定义的索引
            await init_beanie(
                database=self.db,
                document_models=document_models
            )
            
            # 不再需要手动创建索引，Beanie 会自动处理
            # await self._create_indexes()
            
            self._initialized = True
            logger.info("File database initialized successfully with Beanie 2.0.0")
            
        except Exception as e:
            logger.error(f"Failed to initialize file database: {e}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.motor_client:
            self.motor_client.close()
            logger.info("File database connection closed")

# 全局数据库实例
_file_db = None

def init_file_db(motor_client: AsyncIOMotorClient, database_name: str) -> FileDatabase:
    """初始化文件数据库"""
    global _file_db
    _file_db = FileDatabase(motor_client, database_name)
    return _file_db

def get_file_db() -> FileDatabase:
    """获取文件数据库实例"""
    if _file_db is None:
        raise RuntimeError("File database not initialized. Call init_file_db first.")
    return _file_db