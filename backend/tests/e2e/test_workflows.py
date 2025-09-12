import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

class TestWorkflows:
    @pytest.mark.asyncio
    async def test_knowledge_processing_workflow(self, test_client, auth_headers):
        """Test complete knowledge processing workflow."""
        # This test simulates the complete workflow from file upload to knowledge processing
        
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('file.services.file_service.upload_file') as mock_upload, \
             patch('knowledge.services.knowledge_item_service.knowledge_item_service.create_knowledge_item') as mock_create, \
             patch('core.kafka.kafka_manager.send_message') as mock_kafka:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com'
            }
            
            # Mock file upload
            from file.models import FileMetadata, FileStatus
            mock_file = FileMetadata(
                id="test-file-123",
                filename="test.pdf",
                file_size=1024,
                content_type="application/pdf",
                status=FileStatus.UPLOADED,
                uploaded_by="test-user-123"
            )
            mock_upload.return_value = mock_file
            
            # Mock knowledge item creation
            from knowledge.models.knowledge_item import KnowledgeItem
            mock_item = KnowledgeItem(
                id="test-item-123",
                title="Test Knowledge Item",
                type="file",
                created_by="test-user-123"
            )
            mock_create.return_value = mock_item
            
            # Step 1: Upload file
            files = {
                "file": ("test.pdf", b"test content", "application/pdf")
            }
            data = {
                "metadata": '{"filename": "test.pdf", "content_type": "application/pdf"}'
            }
            
            upload_response = test_client.post(
                "/api/files/upload",
                files=files,
                data=data,
                headers=auth_headers
            )
            assert upload_response.status_code == 200
            
            # Step 2: Create knowledge item
            item_data = {
                "title": "Test Knowledge Item",
                "type": "file",
                "source_urls": ["https://example.com/test.pdf"],
                "file_ids": ["test-file-123"],
                "tags": ["test", "document"],
                "knowledge_base_ids": []
            }
            
            item_response = test_client.post(
                "/api/knowledge/items",
                json=item_data,
                headers=auth_headers
            )
            assert item_response.status_code == 200
            
            # Verify Kafka message was sent for processing
            assert mock_kafka.called