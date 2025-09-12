import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

class TestKnowledgeAPI:
    @pytest.mark.asyncio
    async def test_create_knowledge_item(self, test_client, auth_headers):
        """Test creating knowledge item API."""
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('knowledge.services.knowledge_item_service.knowledge_item_service.create_knowledge_item') as mock_create:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com'
            }
            
            # Mock created item
            from knowledge.models.knowledge_item import KnowledgeItem
            mock_item = KnowledgeItem(
                title="Test Item",
                type="file",
                created_by="test-user-123"
            )
            mock_create.return_value = mock_item
            
            item_data = {
                "title": "Test Item",
                "type": "file",
                "description": "Test description",
                "source_urls": ["https://example.com/test.pdf"],
                "file_ids": ["test-file-123"],
                "tags": ["test", "document"],
                "knowledge_base_ids": []
            }
            
            response = test_client.post(
                "/api/knowledge/items",
                json=item_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Item"

    @pytest.mark.asyncio
    async def test_list_knowledge_items(self, test_client, auth_headers):
        """Test listing knowledge items API."""
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('knowledge.services.knowledge_item_service.knowledge_item_service.list_user_knowledge_items') as mock_list:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com'
            }
            
            # Mock items list
            from knowledge.models.knowledge_item import KnowledgeItem
            mock_items = [
                KnowledgeItem(
                    title="Item 1",
                    type="file",
                    created_by="test-user-123"
                ),
                KnowledgeItem(
                    title="Item 2",
                    type="webpage",
                    created_by="test-user-123"
                )
            ]
            mock_list.return_value = mock_items
            
            response = test_client.get(
                "/api/knowledge/items?skip=0&limit=10",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2