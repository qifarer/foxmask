from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from foxmask.core.config import get_settings

settings = get_settings()

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()

async def connect_to_mongo():
    """连接到 MongoDB"""
    try:
        # 构建连接字符串
        connection_string = settings.MONGO_URI
        '''
        if settings.MONGO_USERNAME and settings.MONGO_PASSWORD:
            # 插入认证信息
            host_part = connection_string.split("://")[1]
            connection_string = (
                f"mongodb://{settings.MONGO_USERNAME}:{settings.MONGO_PASSWORD}@{host_part}"
                f"?authSource={settings.MONGO_AUTH_SOURCE}"
            )
        '''
        print("Connecting to MongoDB with URI:", connection_string)
        mongodb.client = AsyncIOMotorClient(connection_string)
        
        # 测试连接
        await mongodb.client.admin.command('ping')
        
        # 设置数据库
        mongodb.database = mongodb.client[settings.MONGO_DB]
        
    except ConnectionFailure as e:
        raise

async def close_mongo_connection():
    """关闭 MongoDB 连接"""
    if mongodb.client:
        mongodb.client.close()

async def get_mongo_db():
    """获取数据库实例"""
    if mongodb.database is None:
        raise RuntimeError("MongoDB is not connected")
    return mongodb.database
 
async def get_file_collection():
    """获取文件集合"""
    db = await get_mongo_db()
    return db[settings.MONGO_FILE_COLLECTION]

async def get_docs_collection():
    """获取文档集合"""
    db = await get_mongo_db()
    return db[settings.MONGO_FILE_COLLECTION]


async def get_kb_collection():
    """获取知识库集合"""
    db = await get_mongo_db()
    return db[settings.MONGO_KB_COLLECTION]


