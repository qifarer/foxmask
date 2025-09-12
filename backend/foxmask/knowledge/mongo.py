# -*- coding: utf-8 -*-
# foxmask/knowledge/mongo.py
# MongoDB initialization and index setup for knowledge items and knowledge bases

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from .models.knowledge_item import KnowledgeItem
from .models.knowledge_base import KnowledgeBase

async def init_knowledge_db(client: AsyncIOMotorClient, db_name: str):
    """Initialize knowledge database with indexes"""
    await init_beanie(
        database=client[db_name],
        document_models=[KnowledgeItem, KnowledgeBase],
    )
    
    # Create indexes
    await KnowledgeItem.get_motor_collection().create_index("type")
    await KnowledgeItem.get_motor_collection().create_index("status")
    await KnowledgeItem.get_motor_collection().create_index("tags")
    await KnowledgeItem.get_motor_collection().create_index("knowledge_base_ids")
    await KnowledgeItem.get_motor_collection().create_index("created_by")
    await KnowledgeItem.get_motor_collection().create_index("created_at")
    
    await KnowledgeBase.get_motor_collection().create_index("is_public")
    await KnowledgeBase.get_motor_collection().create_index("tags")
    await KnowledgeBase.get_motor_collection().create_index("created_by")
    await KnowledgeBase.get_motor_collection().create_index("created_at")