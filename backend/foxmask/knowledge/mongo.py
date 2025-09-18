# -*- coding: utf-8 -*-
# foxmask/knowledge/mongo.py
# MongoDB initialization and index setup for knowledge items and knowledge bases

# 标准库导入
import asyncio

# 第三方库导入
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

# 本地模块导入
from foxmask.core.config import settings
from foxmask.core.logger import logger
from .models.knowledge_item import KnowledgeItem, KnowledgeItemContent
from .models.knowledge_base import KnowledgeBase


async def init_knowledge_db() -> None:
    """
    初始化知识库数据库连接
    
    Raises:
        Exception: 数据库初始化失败时抛出异常
    """
    try:
        # 创建MongoDB客户端连接
        client = AsyncIOMotorClient(str(settings.MONGODB_URI))
        database = client[settings.MONGODB_DB_NAME]
        
        logger.info(f"Connecting to MongoDB database for knowledge: {settings.MONGODB_DB_NAME}")
        
        # 在初始化之前清理冲突的索引（可选）
        await cleanup_conflicting_indexes(database)
        
        # 初始化Beanie ODM
        await init_beanie(
            database=database,
            document_models=[KnowledgeItem, KnowledgeBase, KnowledgeItemContent],
        )
        
        logger.info("Knowledge database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize knowledge database: {e}")
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
        # 清理知识项集合的冲突索引
        knowledge_item_collection = database["knowledge_items"]
        knowledge_base_collection = database["knowledge_bases"]
        knowledge_content_collection = database["knowledge_item_contents"]
        
        collections_to_clean = [
            ("knowledge_items", knowledge_item_collection),
            ("knowledge_bases", knowledge_base_collection),
            ("knowledge_item_contents", knowledge_content_collection)
        ]
        
        total_indexes_removed = 0
        
        for collection_name, collection in collections_to_clean:
            logger.debug(f"Starting index cleanup for {collection_name} collection")
            
            try:
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
                    
                    # 删除可能冲突的索引（根据您的模型定义调整）
                    if collection_name == "knowledge_items":
                        # 删除可能与 KnowledgeItem 模型冲突的索引
                        if any(field in index_key for field in ["tenant_id", "item_type", "status", "created_by"]):
                            if not index_name.startswith("knowledge_items_"):
                                logger.info(f"Removing conflicting index from knowledge_items: {index_name}")
                                await collection.drop_index(index_name)
                                indexes_removed += 1
                    
                    elif collection_name == "knowledge_bases":
                        # 删除可能与 KnowledgeBase 模型冲突的索引
                        if any(field in index_key for field in ["tenant_id", "visibility", "owner_id"]):
                            if not index_name.startswith("knowledge_bases_"):
                                logger.info(f"Removing conflicting index from knowledge_bases: {index_name}")
                                await collection.drop_index(index_name)
                                indexes_removed += 1
                    
                    elif collection_name == "knowledge_item_contents":
                        # 删除可能与 KnowledgeItemContent 模型冲突的索引
                        if any(field in index_key for field in ["item_id", "content_type", "tenant_id"]):
                            if not index_name.startswith("knowledge_item_contents_"):
                                logger.info(f"Removing conflicting index from knowledge_item_contents: {index_name}")
                                await collection.drop_index(index_name)
                                indexes_removed += 1
                
                total_indexes_removed += indexes_removed
                if indexes_removed > 0:
                    logger.info(f"Removed {indexes_removed} conflicting indexes from {collection_name}")
                    
            except Exception as e:
                logger.warning(f"Error during index cleanup for {collection_name}: {e}")
                continue
        
        if total_indexes_removed > 0:
            logger.info(f"Total removed {total_indexes_removed} conflicting indexes")
        else:
            logger.debug("No conflicting indexes found in knowledge collections")
            
    except Exception as e:
        logger.warning(f"Error during knowledge index cleanup: {e}")
        # 继续执行，让 Beanie 处理索引创建


async def init_knowledge_db_with_client(client: AsyncIOMotorClient, db_name: str = None) -> None:
    """
    使用现有的MongoDB客户端初始化知识库数据库
    
    Args:
        client: 已连接的MongoDB客户端
        db_name: 数据库名称（可选，如果为None则使用配置中的名称）
    """
    try:
        database_name = db_name or settings.MONGODB_DB_NAME
        database = client[database_name]
        
        logger.info(f"Initializing knowledge database with existing client: {database_name}")
        
        # 初始化Beanie ODM
        await init_beanie(
            database=database,
            document_models=[KnowledgeItem, KnowledgeBase, KnowledgeItemContent],
        )
        
        logger.info("Knowledge database initialized successfully with existing client")
        
    except Exception as e:
        logger.error(f"Failed to initialize knowledge database with existing client: {e}")
        raise