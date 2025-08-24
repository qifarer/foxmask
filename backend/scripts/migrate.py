# scripts/migrate.py
#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from foxmask.core.database import connect_to_mongo, get_database

async def migrate_database():
    """Perform database migrations"""
    await connect_to_mongo()
    db = get_database()
    
    # Example migration: add new fields to existing collections
    # This is where you would add any database migration logic
    
    print("Database migrations completed successfully")
    
    # Close connection
    from foxmask.core.database import close_mongo_connection
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(migrate_database())