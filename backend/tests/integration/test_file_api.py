import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

class TestFileAPI:
    @pytest.mark.asyncio
    async def test_upload_file(self, test_client, auth_headers):
        """Test file upload API."""
        # Mock dependencies
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('file.services.file_service.upload_file') as mock_upload:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com'
            }
            
            # Mock upload response
            from file.models import FileMetadata, FileStatus
            mock_file = FileMetadata(
                filename="test.pdf",
                file_size=1024,
                content_type="application/pdf",
                status=FileStatus.UPLOADED,
                uploaded_by="test-user-123"
            )
            mock_upload.return_value = mock_file
            
            # Create multipart form data
            files = {
                "file": ("test.pdf", b"test content", "application/pdf")
            }
            data = {
                "metadata": '{"filename": "test.pdf", "content_type": "application/pdf", "description": "Test file"}'
            }
            
            response = test_client.post(
                "/api/files/upload",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_download_file(self, test_client, auth_headers):
        """Test file download API."""
        with patch('utils.casdoor_client.casdoor_client.get_user_info') as mock_user_info, \
             patch('file.services.file_service.get_presigned_download_url') as mock_url:
            
            mock_user_info.return_value = {
                'id': 'test-user-123',
                'name': 'testuser',
                'email': 'test@example.com'
            }
            
            mock_url.return_value = "http://presigned-url.com/test.pdf"
            
            response = test_client.get(
                "/api/files/test-file-123/download",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["download_url"] == "http://presigned-url.com/test.pdf"