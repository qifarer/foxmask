# tests/test_task.py
import pytest
from app.domains.task.services import TaskService
from app.domains.task.models import Task, TaskType, TaskStatus

@pytest.mark.asyncio
async def test_create_task(test_database):
    """Test task creation"""
    service = TaskService()
    service.db = test_database
    
    task = await service.create_task(
        TaskType.DOCUMENT_PARSING,
        "test_document_id",
        "test_user"
    )
    
    assert task is not None
    assert task.type == TaskType.DOCUMENT_PARSING
    assert task.status == TaskStatus.PENDING
    assert task.document_id == "test_document_id"