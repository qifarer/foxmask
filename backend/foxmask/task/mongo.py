# -*- coding: utf-8 -*-
# foxmask/task/mongo.py
# MongoDB initialization for task management using Beanie ODM

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from .models import Task

async def init_task_db(client: AsyncIOMotorClient, db_name: str):
    """Initialize task database with indexes"""
    await init_beanie(
        database=client[db_name],
        document_models=[Task],
    )
    
    # Create indexes
    await Task.get_motor_collection().create_index("type")
    await Task.get_motor_collection().create_index("status")
    await Task.get_motor_collection().create_index("priority")
    await Task.get_motor_collection().create_index("scheduled_for")
    await Task.get_motor_collection().create_index("created_by")
    await Task.get_motor_collection().create_index("created_at")
    
    # Compound index for efficient querying
    await Task.get_motor_collection().create_index([
        ("status", 1),
        ("type", 1),
        ("priority", 1)
    ])