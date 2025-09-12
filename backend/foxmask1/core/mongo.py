# foxmask/core/mongo.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import logging
from contextlib import asynccontextmanager
from foxmask.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MongoDBConnection:
    """MongoDB 连接核心管理类"""
    _instance: Optional['MongoDBConnection'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _database = None
    _is_connected: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> AsyncIOMotorClient:
        if not self._client:
            raise RuntimeError("MongoDB client not initialized")
        return self._client

    @property
    def database(self):
        if not self._database:
            raise RuntimeError("MongoDB database not initialized")
        return self._database

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self, max_retries: int = 3, retry_delay: float = 1.0):
        """建立 MongoDB 连接"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                connection_string = self._build_connection_string()
                logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{max_retries})")
                
                self._client = AsyncIOMotorClient(
                    connection_string,
                    maxPoolSize=settings.MONGO_MAX_POOL_SIZE or 100,
                    minPoolSize=settings.MONGO_MIN_POOL_SIZE or 10,
                    serverSelectionTimeoutMS=10000,
                )
                
                # 测试连接
                await self._client.admin.command('ping')
                
                # 设置数据库
                db_name = settings.MONGO_DB or "foxmask"
                self._database = self._client[db_name]
                self._is_connected = True
                
                logger.info(f"Successfully connected to MongoDB database: {db_name}")
                return
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to connect to MongoDB after {max_retries} attempts")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                raise

    async def disconnect(self):
        """关闭 MongoDB 连接"""
        if self._client:
            try:
                self._client.close()
                self._is_connected = False
                self._client = None
                self._database = None
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

    def _build_connection_string(self) -> str:
        """构建连接字符串"""
        if settings.MONGO_URI:
            return settings.MONGO_URI
        
        host = settings.MONGO_HOST or "localhost"
        port = settings.MONGO_PORT or 27017
        
        auth_part = ""
        if settings.MONGO_USERNAME and settings.MONGO_PASSWORD:
            auth_part = f"{settings.MONGO_USERNAME}:{settings.MONGO_PASSWORD}@"
        
        options = []
        if settings.MONGO_AUTH_SOURCE:
            options.append(f"authSource={settings.MONGO_AUTH_SOURCE}")
        if settings.MONGO_REPLICA_SET:
            options.append(f"replicaSet={settings.MONGO_REPLICA_SET}")
        if settings.MONGO_SSL:
            options.append("ssl=true")
        
        options_str = "?" + "&".join(options) if options else ""
        
        return f"mongodb://{auth_part}{host}:{port}/{options_str}"

# 全局连接实例
mongo_connection = MongoDBConnection()