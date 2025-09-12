# foxmask/core/mongo.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional, Dict, Any, List, Type
import logging
from contextlib import asynccontextmanager
from foxmask.core.config import get_settings
from beanie import init_beanie

logger = logging.getLogger(__name__)
settings = get_settings()

class MongoDB:
    """MongoDB 连接管理类（Beanie 2.0.0 兼容）"""
    client: Optional[AsyncIOMotorClient] = None
    database = None
    _is_connected: bool = False
    _connection_string: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected

mongodb = MongoDB()

def _build_connection_string() -> str:
    """构建 MongoDB 连接字符串"""
    if settings.MONGO_URI:
        return settings.MONGO_URI
    
    # 如果没有提供完整的 URI，则构建一个
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

async def init_beanie_with_models():
    """初始化 Beanie 2.0.0 文档模型"""
    try:
        # 动态导入模型以避免循环导入
        from foxmask.file.models import File, FileChunk, FileAccessLog, FileVersion
        
        # Beanie 2.0.0 需要明确的模型类列表
        document_models: List[Type] = [
            File,
            FileChunk,
            FileAccessLog,
            FileVersion,
        ]
        
        # 尝试导入其他模型（可选）
        try:
            from foxmask.auth.models import User
            document_models.append(User)
            logger.debug("User model added to Beanie initialization")
        except ImportError:
            logger.debug("User model not found, skipping")
        
        try:
            from foxmask.tag.models import Tag
            document_models.append(Tag)
            logger.debug("Tag model added to Beanie initialization")
        except ImportError:
            logger.debug("Tag model not found, skipping")
        
        # Beanie 2.0.0 初始化
        await init_beanie(
            database=mongodb.database,
            document_models=document_models  # 直接传递模型类列表
        )
        
        logger.info(f"Beanie 2.0.0 initialized successfully with {len(document_models)} document models")
        
    except Exception as e:
        logger.error(f"Failed to initialize Beanie 2.0.0: {e}", exc_info=True)
        # 不要阻止应用程序启动，某些功能可能不需要 Beanie
        logger.warning("Beanie initialization failed, but continuing without it")

async def create_indexes_after_init():
    """在 Beanie 初始化后创建索引"""
    try:
        # 等待一段时间确保 Beanie 初始化完成
        import asyncio
        await asyncio.sleep(1)
        
        # 手动创建索引
        db = await get_mongo_db()
        
        # 文件集合索引
        files_collection = db["files"]
        await files_collection.create_index("file_id", unique=True)
        await files_collection.create_index("filename")
        await files_collection.create_index([("owner_id", 1), ("tenant_id", 1)])
        await files_collection.create_index([("file_type", 1), ("status", 1)])
        await files_collection.create_index("uploaded_at")
        await files_collection.create_index("is_deleted")
        
        # 文本索引（用于搜索）
        await files_collection.create_index([("filename", "text"), ("tags", "text")])
        
        # 文件分块索引
        chunks_collection = db["file_chunks"]
        await chunks_collection.create_index([("file_id", 1), ("chunk_number", 1)], unique=True)
        
        # 文件版本索引
        versions_collection = db["file_versions"]
        await versions_collection.create_index([("file_id", 1), ("version", 1)], unique=True)
        
        # 访问日志索引
        access_logs_collection = db["file_access_logs"]
        await access_logs_collection.create_index([("file_id", 1), ("accessed_at", -1)])
        await access_logs_collection.create_index("accessed_at", expireAfterSeconds=2592000)  # 30天过期
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

async def connect_to_mongo(max_retries: int = 3, retry_delay: float = 1.0):
    """连接到 MongoDB，支持重试机制"""
    import asyncio
    
    for attempt in range(max_retries):
        try:
            connection_string = _build_connection_string()
            logger.info(f"Connecting to MongoDB (attempt {attempt + 1}/{max_retries})")
            
            # 创建客户端
            mongodb.client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=settings.MONGO_MAX_POOL_SIZE or 100,
                minPoolSize=settings.MONGO_MIN_POOL_SIZE or 10,
            )
            
            # 测试连接
            await mongodb.client.admin.command('ping')
            
            # 设置数据库
            db_name = settings.MONGO_DB or "foxmask"
            mongodb.database = mongodb.client[db_name]
            mongodb._is_connected = True
            mongodb._connection_string = connection_string
            
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
            
            # 初始化 Beanie 2.0.0
            await init_beanie_with_models()
            
            # 创建索引
            await create_indexes_after_init()
            
            return
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts")
                raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

async def close_mongo_connection():
    """关闭 MongoDB 连接"""
    if mongodb.client:
        try:
            mongodb.client.close()
            mongodb._is_connected = False
            mongodb.client = None
            mongodb.database = None
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")

async def get_mongo_db():
    """获取数据库实例，如果未连接则自动连接"""
    if not mongodb.is_connected or mongodb.database is None:
        try:
            await connect_to_mongo()
        except Exception as e:
            logger.error("Failed to connect to MongoDB")
            raise RuntimeError(f"MongoDB is not connected: {e}")
    
    return mongodb.database

async def get_collection(collection_name: str):
    """获取指定的集合"""
    db = await get_mongo_db()
    return db[collection_name]

async def get_file_collection():
    """获取文件集合"""
    collection_name = settings.MONGO_FILE_COLLECTION or "files"
    return await get_collection(collection_name)

async def get_docs_collection():
    """获取文档集合"""
    collection_name = settings.MONGO_DOCS_COLLECTION or "documents"
    return await get_collection(collection_name)

async def get_kb_collection():
    """获取知识库集合"""
    collection_name = settings.MONGO_KB_COLLECTION or "knowledge_bases"
    return await get_collection(collection_name)

async def get_user_collection():
    """获取用户集合"""
    collection_name = settings.MONGO_USER_COLLECTION or "users"
    return await get_collection(collection_name)

async def get_audit_collection():
    """获取审计日志集合"""
    collection_name = settings.MONGO_AUDIT_COLLECTION or "audit_logs"
    return await get_collection(collection_name)

async def check_connection() -> bool:
    """检查 MongoDB 连接状态"""
    try:
        if mongodb.client:
            await mongodb.client.admin.command('ping')
            return True
        return False
    except Exception:
        return False

async def get_database_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    try:
        db = await get_mongo_db()
        stats = await db.command("dbStats")
        return stats
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

@asynccontextmanager
async def mongo_session():
    """MongoDB 会话上下文管理器"""
    session = None
    try:
        client = mongodb.client
        if client:
            async with await client.start_session() as session:
                yield session
        else:
            yield None
    except Exception as e:
        logger.error(f"MongoDB session error: {e}")
        raise
    finally:
        if session:
            await session.end_session()

# 添加连接状态检查装饰器
def require_mongo_connection(func):
    """装饰器：确保 MongoDB 连接已建立"""
    async def wrapper(*args, **kwargs):
        if not mongodb.is_connected:
            await connect_to_mongo()
        return await func(*args, **kwargs)
    return wrapper