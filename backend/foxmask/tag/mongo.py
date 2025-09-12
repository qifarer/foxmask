# -*- coding: utf-8 -*-
# foxmask/tag/mongo.py
# MongoDB initialization and index setup for tag management

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from .models import Tag

async def init_tag_db(client: AsyncIOMotorClient, db_name: str):
    """Initialize tag database with indexes"""
    await init_beanie(
        database=client[db_name],
        document_models=[Tag],
    )
    
    # Create indexes
    await Tag.get_motor_collection().create_index("name")
    await Tag.get_motor_collection().create_index("type")
    await Tag.get_motor_collection().create_index("created_by")
    await Tag.get_motor_collection().create_index("is_active")
    await Tag.get_motor_collection().create_index("usage_count")
    
    # Create unique index on name
    await Tag.get_motor_collection().create_index("name", unique=True)