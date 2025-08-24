# scripts/init_db.py
#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from foxmask.core.database import connect_to_mongo, get_database
from foxmask.core.config import get_settings

async def init_database():
    """Initialize database with collections and indexes"""
    await connect_to_mongo()
    db = get_database()
    
    # Create indexes for better query performance
    await db.files.create_index("id")
    await db.files.create_index("owner")
    await db.files.create_index([("owner", 1), ("uploaded_at", -1)])
    
    await db.documents.create_index("id")
    await db.documents.create_index("owner")
    await db.documents.create_index([("owner", 1), ("created_at", -1)])
    await db.documents.create_index([("owner", 1), ("status", 1)])
    
    await db.tasks.create_index("id")
    await db.tasks.create_index("owner")
    await db.tasks.create_index("document_id")
    await db.tasks.create_index([("owner", 1), ("created_at", -1)])
    await db.tasks.create_index([("owner", 1), ("status", 1)])
    
    print("Database initialized successfully")
    
    # Close connection
    from foxmask.core.database import close_mongo_connection
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(init_database())