# tests/conftest.py
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Create a test database connection"""
    settings = get_settings()
    # Use a test database
    test_mongo_uri = settings.MONGODB_URI + "_test"
    client = AsyncIOMotorClient(test_mongo_uri)
    database = client[settings.MONGODB_DB + "_test"]
    
    yield database
    
    # Clean up
    await client.drop_database(settings.MONGODB_DB + "_test")
    client.close()