from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ..services.file import file_service
from ..models.file import FileResponse, FileListResponse

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/", response_model=FileListResponse)
async def get_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取所有文件"""
    return await file_service.get_all_files(skip, limit)

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(file_id: str):
    """根据ID获取文件"""
    return await file_service.get_file_by_id(file_id)

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    success = await file_service.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}

@router.get("/knowledge-base/{kb_id}", response_model=List[FileResponse])
async def get_files_by_knowledge_base(kb_id: str):
    """根据知识库ID获取文件"""
    return await file_service.get_files_by_knowledge_base(kb_id)