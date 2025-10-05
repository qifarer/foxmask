# -*- coding: utf-8 -*-
# tests/test_upload_service.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.foxmask.file.services.upload_1 import UploadService
from foxmask.file.repositories.upload import UploadRepository
from foxmask.file.services.file import FileService
from foxmask.file.dtos.upload import UploadTaskCreateDTO
from foxmask.file.models.upload import UploadSourceType, UploadStrategy, Status

@pytest.fixture
async def mock_repo():
    repo = AsyncMock(spec=UploadRepository)
    return repo

@pytest.fixture
async def mock_file_service():
    return AsyncMock(spec=FileService)

@pytest.mark.asyncio
async def test_create_upload_task(mock_repo, mock_file_service):
    service = UploadService(mock_repo, mock_file_service)
    dto = UploadTaskCreateDTO(
        task_type="FILE_UPLOAD",
        source_type=UploadSourceType.SINGLE_FILE,
        source_paths=["/path/to/file.txt"],
        title="Test Upload Task"
    )
    mock_task = AsyncMock(id="task_id", uid="task_uid")
    mock_repo.create_task.return_value = mock_task

    task = await service.create_upload_task("tenant_id", dto)
    assert task.id == "task_id"
    mock_repo.create_task.assert_called_once()