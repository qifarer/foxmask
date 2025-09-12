import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from unittest.mock import AsyncMock, MagicMock, patch

from main import app
from foxmask.core.config import settings
from foxmask.core.mongo import MongoDB
from foxmask.auth.models import User
from foxmask.file.models import FileMetadata
from foxmask.knowledge.models.knowledge_item import KnowledgeItem
from foxmask.knowledge.models.knowledge_base import KnowledgeBase
from foxmask.tag.models import Tag
from foxmask.task.models import Task

# Test database name
TEST_DB_NAME = "foxmask_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create a test database connection."""
    # Create test MongoDB client
    test_mongodb = MongoDB()
    test_mongodb.client = AsyncIOMotorClient(str(settings.MONGODB_URI))
    test_mongodb.database = test_mongodb.client[TEST_DB_NAME]
    
    # Initialize beanie with test database
    documents = [User, FileMetadata, KnowledgeItem, KnowledgeBase, Tag, Task]
    await init_beanie(
        database=test_mongodb.database,
        document_models=documents,
    )
    
    yield test_mongodb.database
    
    # Cleanup: drop test database
    await test_mongodb.client.drop_database(TEST_DB_NAME)
    test_mongodb.client.close()

@pytest.fixture(scope="function")
def test_client(test_db):
    """Create a test client with overridden dependencies."""
    
    # Mock external dependencies
    with patch('core.mongo.mongodb.database', test_db), \
         patch('utils.minio_client.minio_client') as mock_minio, \
         patch('utils.weaviate_client.weaviate_client') as mock_weaviate, \
         patch('utils.neo4j_client.neo4j_client') as mock_neo4j, \
         patch('utils.casdoor_client.casdoor_client') as mock_casdoor:
        
        # Setup mocks
        mock_minio.upload_file = AsyncMock(return_value=True)
        mock_minio.download_file = AsyncMock(return_value=b"test file content")
        mock_minio.get_presigned_url = AsyncMock(return_value="http://test-presigned-url.com")
        mock_minio.file_exists = AsyncMock(return_value=True)
        
        mock_weaviate_client.connect = AsyncMock()
        mock_weaviate_client.create_object = AsyncMock(return_value="test-vector-id")
        
        mock_neo4j_client.connect = AsyncMock()
        mock_neo4j_client.create_node = AsyncMock(return_value="test-graph-id")
        
        mock_casdoor_client.get_user_info = AsyncMock(return_value={
            'id': 'test-user-id',
            'name': 'testuser',
            'email': 'test@example.com',
            'displayName': 'Test User'
        })
        mock_casdoor_client.verify_token = AsyncMock(return_value=True)
        
        # Create test client
        with TestClient(app) as client:
            yield client

@pytest.fixture(scope="function")
def mock_user_data():
    """Provide mock user data."""
    return {
        "casdoor_id": "test-user-123",
        "name": "testuser",
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar": "https://example.com/avatar.jpg",
        "is_active": True,
        "is_superuser": False
    }

@pytest.fixture(scope="function")
def mock_knowledge_item_data():
    """Provide mock knowledge item data."""
    return {
        "title": "Test Knowledge Item",
        "description": "Test description",
        "type": "file",
        "source_urls": ["https://example.com/test.pdf"],
        "file_ids": ["test-file-123"],
        "tags": ["test", "document"],
        "category": "Test Category",
        "created_by": "test-user-123"
    }

@pytest.fixture(scope="function")
def mock_file_data():
    """Provide mock file data."""
    return {
        "filename": "test.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "minio_object_name": "user123/test.pdf",
        "minio_bucket": "foxmask-test",
        "uploaded_by": "test-user-123"
    }

@pytest.fixture(scope="function")
def auth_headers():
    """Provide authentication headers for tests."""
    return {
        "Authorization": "Bearer test-token-123"
    }

@pytest.fixture(scope="function")
def mock_kafka():
    """Mock AIOKafka manager"""
    with patch('core.kafka.kafka_manager') as mock:
        mock.send_message = AsyncMock()
        mock.create_consumer = AsyncMock()
        mock.create_producer = AsyncMock()
        mock.consume_messages = AsyncMock()
        
        # Mock the async generator
        async def mock_consume_generator(*args, **kwargs):
            # Yield some test messages
            test_messages = [
                {'value': {'message_id': 'test-msg-1', 'topic': 'test-topic'}},
                {'value': {'message_id': 'test-msg-2', 'topic': 'test-topic'}}
            ]
            for msg in test_messages:
                yield msg
                await asyncio.sleep(0.01)
                
        mock.consume_messages.return_value = mock_consume_generator()
        yield mock