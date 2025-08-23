# tests/test_document.py
import pytest
from app.domains.document.services import DocumentService
from app.domains.document.models import Document, DocumentStatus

@pytest.mark.asyncio
async def test_create_document(test_database):
    """Test document creation"""
    service = DocumentService()
    service.db = test_database
    
    document = await service.create_document(
        "Test Document",
        "This is a test document",
        ["file1", "file2"],
        "test_user"
    )
    
    assert document is not None
    assert document.title == "Test Document"
    assert document.status == DocumentStatus.CREATED
    assert document.file_ids == ["file1", "file2"]