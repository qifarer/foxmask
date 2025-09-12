# foxmask/document/routers.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.schemas import User
from foxmask.document.services import DocumentService
from foxmask.document.schemas import (
    DocumentCreate, DocumentResponse, DocumentUpdate, DocumentDetailResponse,
    DocumentListResponse, DocumentFilter, PaginationParams, DocumentWithContentResponse,
    DocumentWithFilesResponse, FileCreate, FileResponse, ContentCreate, ContentResponse
)
from foxmask.core.exceptions import NotFoundError, ServiceError
from foxmask.document.models import DocumentStatus, DocumentSourceType

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user)
):
    """创建新文档"""
    service = DocumentService()
    try:
        new_document = await service.create_document(
            document,
            current_user.id,
            current_user
        )
        return new_document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[DocumentStatus] = None,
    source_type: Optional[DocumentSourceType] = None,
    tags: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """获取文档列表"""
    service = DocumentService()
    try:
        documents = await service.list_documents(
            current_user.id, 
            skip, 
            limit,
            status,
            source_type.value if source_type else None,
            tags
        )
        
        total_count = await service.docs_collection.count_documents({"owner": current_user.id})
        
        return DocumentListResponse(
            items=documents,
            total=total_count,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取单个文档详情"""
    service = DocumentService()
    document = await service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.get("/{document_id}/with-content", response_model=DocumentWithContentResponse)
async def get_document_with_content(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取文档及其内容"""
    service = DocumentService()
    document = await service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    content = await service.get_content_by_document(document_id) if document.content_id else None
    
    response_data = document.model_dump()
    response_data["content"] = content.model_dump() if content else None
    
    return DocumentWithContentResponse(**response_data)

@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新文档信息"""
    service = DocumentService()
    document = await service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # 构建更新数据
    update_data = {}
    if document_update.title is not None:
        update_data["title"] = document_update.title
    if document_update.description is not None:
        update_data["description"] = document_update.description
    if document_update.metadata is not None:
        update_data["metadata"] = document_update.metadata
    if document_update.tags is not None:
        update_data["tags"] = document_update.tags
    
    update_data["updated_at"] = datetime.utcnow()
    
    await service.docs_collection.update_one(
        {"id": document_id},
        {"$set": update_data}
    )
    
    # 返回更新后的文档
    updated_document = await service.get_document(document_id, current_user.id)
    return updated_document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除文档"""
    service = DocumentService()
    try:
        await service.delete_document(document_id, current_user.id, current_user)
        return None
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# 文件相关路由
@router.post("/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(
    file: FileCreate,
    current_user: User = Depends(get_current_user)
):
    """创建文件记录"""
    service = DocumentService()
    try:
        new_file = await service.create_file(file, current_user.id)
        return new_file
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取文件信息"""
    service = DocumentService()
    file = await service.get_file(file_id, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return file

# 内容相关路由
@router.post("/contents", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    content: ContentCreate,
    current_user: User = Depends(get_current_user)
):
    """创建内容记录"""
    service = DocumentService()
    try:
        # 验证用户有权限操作该文档
        document = await service.get_document(content.document_id, current_user.id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        new_content = await service.create_content(content)
        return new_content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/contents/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取内容信息"""
    service = DocumentService()
    content = await service.get_content(content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # 验证用户有权限访问该内容对应的文档
    document = await service.get_document(content.document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return content