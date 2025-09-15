# -*- coding: utf-8 -*-
# foxmask/file/mongo.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky

# 标准库导入
import asyncio

# 第三方库导入
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

# 本地模块导入
from foxmask.core.config import settings
from foxmask.file.models import File, FileChunk
from foxmask.core.logger import logger


async def init_file_db() -> None:
    """
    初始化文件数据库连接
    
    Raises:
        Exception: 数据库初始化失败时抛出异常
    """
    try:
        # 创建MongoDB客户端连接
        client = AsyncIOMotorClient(str(settings.MONGODB_URI))
        database = client[settings.MONGODB_DB_NAME]
        
        logger.info(f"Connecting to MongoDB database: {settings.MONGODB_DB_NAME}")
        
        # 在初始化之前清理冲突的索引
        await cleanup_conflicting_indexes(database)
        
        # 初始化Beanie ODM
        await init_beanie(
            database=database,
            document_models=[File, FileChunk],
        )
        
        logger.info("File database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize file database: {e}")
        raise


async def cleanup_conflicting_indexes(database) -> None:
    """
    清理初始化前的冲突索引
    
    Args:
        database: MongoDB数据库实例
        
    Note:
        此函数用于清理可能与Beanie自动生成的索引冲突的旧索引
    """
    try:
        collection = database["file_chunks"]
        
        logger.debug("Starting index cleanup for file_chunks collection")
        
        # 获取现有索引
        existing_indexes = await collection.list_indexes().to_list()
        
        # 检查并删除冲突的索引
        indexes_removed = 0
        for index in existing_indexes:
            index_name = index.get("name")
            index_key = index.get("key", {})
            
            # 跳过默认的 _id 索引
            if index_name == "_id_":
                continue
            
            # 删除与 file_id + chunk_number 相关的旧索引
            if index_key.get("file_id") and index_key.get("chunk_number"):
                if index_name != "file_chunk_unique":
                    logger.info(f"Removing conflicting composite index: {index_name}")
                    await collection.drop_index(index_name)
                    indexes_removed += 1
            
            # 删除其他可能冲突的单字段索引
            elif index_name in ["file_id_chunk_number", "file_id_status", 
                              "upload_id", "created_at", "status"]:
                logger.info(f"Removing old single-field index: {index_name}")
                await collection.drop_index(index_name)
                indexes_removed += 1
        
        if indexes_removed > 0:
            logger.info(f"Removed {indexes_removed} conflicting indexes")
        else:
            logger.debug("No conflicting indexes found")
            
    except Exception as e:
        logger.warning(f"Error during index cleanup: {e}")
        # 继续执行，让 Beanie 处理索引创建