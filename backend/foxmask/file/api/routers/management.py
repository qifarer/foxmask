# -*- coding: utf-8 -*-
# foxmask/file/api/routers/file_router.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from foxmask.file.services import get_service_manager
from foxmask.file.api.schemas import (
    FileCreateRequest, FileUpdateRequest, FileResponse, FileListResponse,
    FileQueryParams, FileStatsResponse, FileUploadRequest, FileUploadResponse,
    FileDownloadResponse, BaseResponse
)

logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/files", tags=["文件管理"])

# 安全依赖
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户（简化实现）"""
    # 这里应该实现真实的JWT令牌验证
    # 目前使用简化实现，从令牌中提取用户信息
    token = credentials.credentials
    # 模拟解析令牌获取用户信息
    return {
        "user_id": "user_123",  # 从令牌中解析
        "tenant_id": "tenant_123",  # 从令牌中解析
        "roles": ["user"]
    }

async def get_current_tenant(user: dict = Depends(get_current_user)):
    """获取当前租户"""
    return user["tenant_id"]

async def get_current_user_id(user: dict = Depends(get_current_user)):
    """获取当前用户ID"""
    return user["user_id"]


@router.post(
    "/",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建文件记录",
    description="创建新的文件记录"
)
async def create_file(
    request: FileCreateRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """创建文件记录"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 转换请求为DTO
        create_dto = FileCreateDTO(
            original_filename=request.original_filename,
            file_size=request.file_size,
            content_type=request.content_type,
            extension=request.extension,
            file_type=request.file_type,
            storage_bucket=request.storage_bucket,
            storage_key=request.storage_key,
            storage_path=request.storage_path,
            checksum_md5=request.checksum_md5,
            checksum_sha256=request.checksum_sha256,
            title=request.title or request.original_filename,
            desc=request.desc,
            category=request.category,
            tags=request.tags,
            note=request.note,
            visibility=request.visibility,
            allowed_users=request.allowed_users,
            allowed_roles=request.allowed_roles,
            metadata=request.metadata
        )
        
        # 调用服务层
        file_dto = await file_service.create_file(create_dto, user_id, tenant_id)
        
        return file_dto
        
    except Exception as e:
        logger.error(f"创建文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建文件失败: {str(e)}"
        )


@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="获取文件详情",
    description="根据文件ID获取文件详细信息"
)
async def get_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取文件详情"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 调用服务层
        file_dto = await file_service.get_file(file_id, user_id, tenant_id)
        
        if not file_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权访问"
            )
        
        return file_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件失败: {str(e)}"
        )


@router.put(
    "/{file_id}",
    response_model=FileResponse,
    summary="更新文件信息",
    description="更新文件的基本信息和元数据"
)
async def update_file(
    file_id: str,
    request: FileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """更新文件信息"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 转换请求为DTO
        update_dto = FileUpdateDTO(
            original_filename=request.original_filename,
            content_type=request.content_type,
            file_type=request.file_type,
            title=request.title,
            desc=request.desc,
            category=request.category,
            tags=request.tags,
            note=request.note,
            file_status=request.file_status,
            visibility=request.visibility,
            allowed_users=request.allowed_users,
            allowed_roles=request.allowed_roles,
            metadata=request.metadata
        )
        
        # 调用服务层
        file_dto = await file_service.update_file(file_id, update_dto, user_id, tenant_id)
        
        if not file_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权访问"
            )
        
        return file_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文件失败: {str(e)}"
        )


@router.delete(
    "/{file_id}",
    response_model=BaseResponse,
    summary="删除文件",
    description="软删除文件（标记为已归档状态）"
)
async def delete_file(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """删除文件"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 调用服务层
        success = await file_service.delete_file(file_id, user_id, tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权访问"
            )
        
        return BaseResponse(
            success=True,
            message="文件删除成功",
            code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件失败: {str(e)}"
        )


@router.get(
    "/",
    response_model=FileListResponse,
    summary="获取文件列表",
    description="获取文件列表，支持分页、筛选和排序"
)
async def list_files(
    title: Optional[str] = Query(None, description="标题关键词"),
    original_filename: Optional[str] = Query(None, description="原始文件名关键词"),
    file_type: Optional[str] = Query(None, description="文件类型"),
    file_status: Optional[str] = Query(None, description="文件状态"),
    content_type: Optional[str] = Query(None, description="内容类型"),
    category: Optional[str] = Query(None, description="分类"),
    tags: Optional[List[str]] = Query(None, description="标签"),
    created_by: Optional[str] = Query(None, description="创建者"),
    visibility: Optional[str] = Query(None, description="可见性"),
    min_size: Optional[int] = Query(None, ge=0, description="最小文件大小"),
    max_size: Optional[int] = Query(None, ge=0, description="最大文件大小"),
    start_date: Optional[str] = Query(None, description="开始时间"),
    end_date: Optional[str] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取文件列表"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 转换查询参数为DTO
        query_dto = FileQueryDTO(
            title=title,
            original_filename=original_filename,
            file_type=file_type,
            file_status=file_status,
            content_type=content_type,
            category=category,
            tags=tags,
            created_by=created_by,
            visibility=visibility,
            min_size=min_size,
            max_size=max_size,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 调用服务层
        list_dto = await file_service.list_files(query_dto, user_id, tenant_id)
        
        return FileListResponse(
            success=True,
            message="获取文件列表成功",
            code=status.HTTP_200_OK,
            items=list_dto.items,
            total=list_dto.total,
            page=list_dto.page,
            size=list_dto.size,
            pages=list_dto.pages
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )


@router.post(
    "/{file_id}/download",
    response_model=BaseResponse,
    summary="记录文件下载",
    description="记录文件下载次数和下载日志"
)
async def record_download(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """记录文件下载"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 获取客户端IP（简化实现）
        # 在实际应用中，应该从请求中获取真实IP
        ip_address = "192.168.1.100"  # 这里应该从请求头中获取
        
        # 调用服务层
        success = await file_service.record_download(file_id, user_id, tenant_id, ip_address)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权访问"
            )
        
        return BaseResponse(
            success=True,
            message="下载记录成功",
            code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录下载失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录下载失败: {str(e)}"
        )


@router.get(
    "/statistics/overview",
    response_model=FileStatsResponse,
    summary="获取文件统计概览",
    description="获取文件的总体统计信息"
)
async def get_file_stats(
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取文件统计信息"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 调用服务层
        stats_dto = await file_service.get_file_stats(tenant_id, user_id)
        
        return FileStatsResponse(
            success=True,
            message="获取文件统计成功",
            code=status.HTTP_200_OK,
            **stats_dto.dict()
        )
        
    except Exception as e:
        logger.error(f"获取文件统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件统计失败: {str(e)}"
        )


@router.post(
    "/upload/prepare",
    response_model=FileUploadResponse,
    summary="准备文件上传",
    description="准备文件上传，生成预签名URL等"
)
async def prepare_upload(
    request: FileUploadRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """准备文件上传"""
    try:
        # 这里可以集成MinIO/S3等存储服务生成预签名URL
        # 实际实现需要根据具体存储方案调整
        
        # 模拟实现
        file_id = f"file_{user_id}_{tenant_id}_{request.filename}"
        upload_url = f"https://storage.example.com/upload/{file_id}"
        
        return FileUploadResponse(
            success=True,
            message="上传准备成功",
            code=status.HTTP_200_OK,
            file_id=file_id,
            upload_url=upload_url
        )
        
    except Exception as e:
        logger.error(f"准备文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"准备文件上传失败: {str(e)}"
        )


@router.get(
    "/{file_id}/download/url",
    response_model=FileDownloadResponse,
    summary="获取文件下载URL",
    description="获取文件的下载URL（预签名URL）"
)
async def get_download_url(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取文件下载URL"""
    try:
        service_manager = get_service_manager()
        file_service = service_manager.file_service
        
        # 先检查文件是否存在和权限
        file_dto = await file_service.get_file(file_id, user_id, tenant_id)
        if not file_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或无权访问"
            )
        
        # 这里可以集成MinIO/S3等存储服务生成预签名URL
        # 模拟实现
        download_url = f"https://storage.example.com/download/{file_id}"
        
        return FileDownloadResponse(
            success=True,
            message="获取下载URL成功",
            code=status.HTTP_200_OK,
            download_url=download_url,
            filename=file_dto.original_filename,
            file_size=file_dto.file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取下载URL失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取下载URL失败: {str(e)}"
        )