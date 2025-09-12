from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
from .config import settings
from typing import List, Type
from beanie import Document

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()

async def connect_to_mongo():
    """Connect to MongoDB and initialize Beanie"""
    try:
        mongodb.client = AsyncIOMotorClient(str(settings.MONGODB_URI))
        mongodb.database = mongodb.client[settings.MONGODB_DB_NAME]
        
        # Import document models
        from foxmask.file.models import File
        from foxmask.knowledge.models.knowledge_item import KnowledgeItem
        from foxmask.knowledge.models.knowledge_base import KnowledgeBase
        from foxmask.tag.models import Tag
        from foxmask.task.models import Task
        
        documents: List[Type[Document]] = [
            File, 
            KnowledgeItem, 
            KnowledgeBase, 
            Tag, 
            Task
        ]
        
        # Initialize beanie with the document models
        await init_beanie(
            database=mongodb.database,
            document_models=documents,
        )
        print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
        
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close MongoDB connection"""
    if mongodb.client:
        mongodb.client.close()
        print("Disconnected from MongoDB")