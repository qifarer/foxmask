# foxmask/file/routers.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import List
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.schemas import User
from foxmask.file.services import FileService
from foxmask.file.schemas import FileUploadResponse, FileListResponse

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    file_id = await service.initiate_upload(
        file.filename,
        file.size,
        file.content_type,
        current_user.id
    )
    
    return FileUploadResponse(file_id=file_id, filename=file.filename)

@router.post("/upload-chunk", status_code=status.HTTP_202_ACCEPTED)
async def upload_chunk(
    file_id: str,
    chunk_index: int,
    chunk_data: bytes,
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    await service.upload_chunk(file_id, chunk_index, chunk_data, current_user.id)
    return {"status": "success"}

@router.post("/complete-upload", response_model=FileMetadata)
async def complete_upload(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    file_meta = await service.complete_upload(file_id, current_user.id)
    return file_meta

@router.get("", response_model=List[FileListResponse])
async def list_files(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    files = await service.list_files(current_user.id, skip, limit)
    return files

@router.get("/{file_id}/download-url")
async def get_download_url(
    file_id: str,
    expires: int = 3600,
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    url = await service.get_presigned_url(file_id, current_user.id, expires)
    return {"url": url}

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    await service.delete_file(file_id, current_user.id)
    return None