# tests/test_file.py
import pytest
from app.domains.file.services import FileService
from app.domains.file.models import FileMetadata, FileStatus

@pytest.mark.asyncio
async def test_initiate_upload(test_database):
    """Test file upload initiation"""
    service = FileService()
    service.db = test_database
    
    file_id = await service.initiate_upload(
        "test.pdf", 
        1024, 
        "application/pdf", 
        "test_user"
    )
    
    assert file_id is not None
    
    # Verify the file metadata was saved
    file_meta = await service.get_file(file_id, "test_user")
    assert file_meta is not None
    assert file_meta.filename == "test.pdf"
    assert file_meta.status == FileStatus.UPLOADING