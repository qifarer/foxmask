# foxmask/infrastructure/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from foxmask.core.config import get_settings

settings = get_settings()

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGO_URI)
    db.database = db.client[settings.MONGO_DB]
    print("Connected to MongoDB")

async def close_mongo_connection():
    db.client.close()
    print("Disconnected from MongoDB")

def get_database():
    return db.database

