import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, UploadFile
from io import BytesIO

from file.services import FileService
from file.models import FileMetadata, FileStatus
from tests.conftest import mock_file_data

class TestFileService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.file_service = FileService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_file_data):
        """Test successful file upload."""
        # Mock MinIO client
        with patch('file.services.minio_client') as mock_minio:
            mock_minio.fput_object = AsyncMock()
            
            # Create mock file
            file_content = b"test file content"
            file = UploadFile(
                filename="test.txt",
                file=BytesIO(file_content),
                content_type="text/plain"
            )
            
            # Create metadata
            from file.schemas import FileMetadataCreate
            metadata = FileMetadataCreate(
                filename="test.txt",
                content_type="text/plain",
                description="Test file",
                tags=["test", "document"]
            )
            
            file_metadata = await self.file_service.upload_file(
                file, "test-user-123", metadata
            )
            
            assert file_metadata is not None
            assert file_metadata.filename == "test.txt"
            assert file_metadata.content_type == "text/plain"
            assert file_metadata.status == FileStatus.UPLOADED
            assert file_metadata.uploaded_by == "test-user-123"

    @pytest.mark.asyncio
    async def test_get_file_metadata(self, mock_file_data):
        """Test getting file metadata."""
        # Create a test file
        file_metadata = FileMetadata(**mock_file_data)
        await file_metadata.insert()
        
        found_metadata = await self.file_service.get_file_metadata(str(file_metadata.id))
        
        assert found_metadata is not None
        assert found_metadata.id == file_metadata.id
        assert found_metadata.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_presigned_download_url(self, mock_file_data):
        """Test generating presigned download URL."""
        # Create a test file
        file_metadata = FileMetadata(**mock_file_data)
        await file_metadata.insert()
        
        # Mock MinIO
        with patch('file.services.minio_client') as mock_minio:
            mock_minio.presigned_get_object = AsyncMock(return_value="http://test-url.com")
            
            url = await self.file_service.get_presigned_download_url(str(file_metadata.id))
            
            assert url == "http://test-url.com"
            mock_minio.presigned_get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_file_data):
        """Test successful file deletion."""
        # Create a test file
        file_metadata = FileMetadata(**mock_file_data)
        await file_metadata.insert()
        
        # Mock MinIO
        with patch('file.services.minio_client') as mock_minio:
            mock_minio.remove_object = AsyncMock()
            
            result = await self.file_service.delete_file(
                str(file_metadata.id), "test-user-123"
            )
            
            assert result is True
            mock_minio.remove_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_nonexistent(self):
        """Test deleting nonexistent file."""
        result = await self.file_service.delete_file("nonexistent-id", "test-user-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_unauthorized(self, mock_file_data):
        """Test unauthorized file deletion."""
        # Create a test file
        file_metadata = FileMetadata(**mock_file_data)
        await file_metadata.insert()
        
        with pytest.raises(HTTPException) as exc_info:
            await self.file_service.delete_file(
                str(file_metadata.id), "different-user-123"
            )
        
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_user_files(self, mock_file_data):
        """Test listing user files."""
        # Create test files for different users
        file1_data = mock_file_data.copy()
        file1_data["uploaded_by"] = "user-1"
        file1 = FileMetadata(**file1_data)
        await file1.insert()
        
        file2_data = mock_file_data.copy()
        file2_data["uploaded_by"] = "user-2"
        file2 = FileMetadata(**file2_data)
        await file2.insert()
        
        # List files for user-1
        user_files = await self.file_service.list_user_files("user-1")
        
        assert len(user_files) == 1
        assert user_files[0].uploaded_by == "user-1"