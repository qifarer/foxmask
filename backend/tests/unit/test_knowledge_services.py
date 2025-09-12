import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from knowledge.services.knowledge_item_service import KnowledgeItemService
from knowledge.services.knowledge_base_service import KnowledgeBaseService
from knowledge.models.knowledge_item import KnowledgeItem, KnowledgeItemStatus, KnowledgeItemType
from knowledge.models.knowledge_base import KnowledgeBase
from tests.conftest import mock_knowledge_item_data

class TestKnowledgeItemService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.knowledge_item_service = KnowledgeItemService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_create_knowledge_item(self, mock_knowledge_item_data):
        """Test creating a knowledge item."""
        # Mock Kafka
        with patch('knowledge.services.knowledge_item_service.kafka_manager') as mock_kafka:
            mock_kafka.send_message = AsyncMock()
            
            from knowledge.schemas import KnowledgeItemCreate
            item_data = KnowledgeItemCreate(**mock_knowledge_item_data)
            
            item = await self.knowledge_item_service.create_knowledge_item(
                item_data, "test-user-123"
            )
            
            assert item is not None
            assert item.title == "Test Knowledge Item"
            assert item.created_by == "test-user-123"
            assert item.status == KnowledgeItemStatus.CREATED
            
            # Verify Kafka message was sent
            mock_kafka.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_knowledge_item(self, mock_knowledge_item_data):
        """Test getting a knowledge item by ID."""
        # Create test item
        item = KnowledgeItem(**mock_knowledge_item_data)
        await item.insert()
        
        found_item = await self.knowledge_item_service.get_knowledge_item(str(item.id))
        
        assert found_item is not None
        assert found_item.id == item.id

    @pytest.mark.asyncio
    async def test_update_knowledge_item(self, mock_knowledge_item_data):
        """Test updating a knowledge item."""
        # Create test item
        item = KnowledgeItem(**mock_knowledge_item_data)
        await item.insert()
        
        from knowledge.schemas import KnowledgeItemUpdate
        update_data = KnowledgeItemUpdate(
            title="Updated Title",
            description="Updated description",
            tags=["updated", "tags"]
        )
        
        # Mock Kafka
        with patch('knowledge.services.knowledge_item_service.kafka_manager') as mock_kafka:
            mock_kafka.send_message = AsyncMock()
            
            updated_item = await self.knowledge_item_service.update_knowledge_item(
                str(item.id), update_data, "test-user-123"
            )
            
            assert updated_item is not None
            assert updated_item.title == "Updated Title"
            assert updated_item.description == "Updated description"
            assert "updated" in updated_item.tags
            
            # Verify status was reset and Kafka message sent
            assert updated_item.status == KnowledgeItemStatus.CREATED
            mock_kafka.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_knowledge_item_unauthorized(self, mock_knowledge_item_data):
        """Test unauthorized knowledge item update."""
        # Create test item
        item = KnowledgeItem(**mock_knowledge_item_data)
        await item.insert()
        
        from knowledge.schemas import KnowledgeItemUpdate
        update_data = KnowledgeItemUpdate(title="Unauthorized Update")
        
        with pytest.raises(HTTPException) as exc_info:
            await self.knowledge_item_service.update_knowledge_item(
                str(item.id), update_data, "different-user-123"
            )
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_knowledge_item(self, mock_knowledge_item_data):
        """Test deleting a knowledge item."""
        # Create test item
        item = KnowledgeItem(**mock_knowledge_item_data)
        await item.insert()
        
        result = await self.knowledge_item_service.delete_knowledge_item(
            str(item.id), "test-user-123"
        )
        
        assert result is True
        
        # Verify item is deleted
        deleted_item = await self.knowledge_item_service.get_knowledge_item(str(item.id))
        assert deleted_item is None

class TestKnowledgeBaseService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.knowledge_base_service = KnowledgeBaseService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_create_knowledge_base(self):
        """Test creating a knowledge base."""
        from knowledge.schemas import KnowledgeBaseCreate
        kb_data = KnowledgeBaseCreate(
            name="Test Knowledge Base",
            description="Test description",
            is_public=True,
            tags=["test", "knowledge"],
            category="Test Category"
        )
        
        kb = await self.knowledge_base_service.create_knowledge_base(
            kb_data, "test-user-123"
        )
        
        assert kb is not None
        assert kb.name == "Test Knowledge Base"
        assert kb.created_by == "test-user-123"
        assert kb.is_public is True

    @pytest.mark.asyncio
    async def test_get_knowledge_base_items(self, mock_knowledge_item_data):
        """Test getting items in a knowledge base."""
        # Create knowledge base
        kb = KnowledgeBase(
            name="Test KB",
            created_by="test-user-123"
        )
        await kb.insert()
        
        # Create knowledge items
        item1_data = mock_knowledge_item_data.copy()
        item1_data["knowledge_base_ids"] = [str(kb.id)]
        item1 = KnowledgeItem(**item1_data)
        await item1.insert()
        
        item2_data = mock_knowledge_item_data.copy()
        item2_data["title"] = "Second Item"
        item2_data["knowledge_base_ids"] = [str(kb.id)]
        item2 = KnowledgeItem(**item2_data)
        await item2.insert()
        
        items = await self.knowledge_base_service.get_knowledge_base_items(str(kb.id))
        
        assert len(items) == 2
        assert items[0].knowledge_base_ids == [str(kb.id)]
        assert items[1].knowledge_base_ids == [str(kb.id)]