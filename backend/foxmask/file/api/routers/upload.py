# -*- coding: utf-8 -*-
# foxmask/file/api/routers/upload_router.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body

from foxmask.file.services import get_service_manager
from foxmask.file.api.schemas import (
    InitializeUploadRequest, UploadChunkRequest, CompleteUploadRequest,
    InitializeUploadResponse, UploadChunkResponse, CompleteUploadResponse,
    GetUploadTaskResponse, ListUploadTasksResponse, ListUploadTaskFilesResponse,
    ResumeUploadResponse, UploadProgressResponse, UploadTaskStatsResponse,
    UploadProcStatusEnum, UploadSourceTypeEnum, UploadStrategyEnum, FileTypeEnum,
    Status  # 添加 Status 枚举
)
from foxmask.file.dtos.upload import (
    InitializeUploadInputDTO, InitializeUploadFileInputDTO,
    UploadChunkInputDTO, CompleteUploadInputDTO, ResumeUploadInputDTO,
    UploadTaskQueryDTO, UploadTaskFileQueryDTO, PaginationParams
)
# 移除重复的枚举导入，使用 schema 中的枚举
from .management import get_current_user_id, get_current_tenant

logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/upload/tasks", tags=["上传任务"])


@router.post(
    "/initialize",
    response_model=InitializeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="初始化上传任务",
    description="创建新的文件上传任务"
)
async def initialize_upload(
    request: InitializeUploadRequest,
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """初始化上传任务"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 转换请求为DTO
        input_dto = InitializeUploadInputDTO(
            tenant_id=tenant_id,
            created_by=user_id,
            title=request.title,
            desc=request.desc,
            source_type=request.source_type,
            source_paths=request.source_paths,
            upload_strategy=request.upload_strategy,
            max_parallel_uploads=request.max_parallel_uploads,
            chunk_size=request.chunk_size,
            preserve_structure=request.preserve_structure,
            base_upload_path=request.base_upload_path,
            auto_extract_metadata=request.auto_extract_metadata,
            file_type_filters=request.file_type_filters,
            max_file_size=request.max_file_size,
            resume_task_id=request.resume_task_id,
            files=[
                InitializeUploadFileInputDTO(
                    original_path=file.original_path,
                    filename=file.filename,
                    file_size=file.file_size,
                    file_type=file.file_type,
                    content_type=file.content_type,
                    extension=file.extension,
                    chunk_size=file.chunk_size
                ) for file in (request.files or [])
            ]
        )
        
        # 调用服务层
        response_dto = await upload_service.initialize_upload(input_dto)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "初始化上传任务失败"
            )
        
        # 确保返回的是正确的响应类型
        return InitializeUploadResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"初始化上传任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化上传任务失败: {str(e)}"
        )


@router.post(
    "/{task_id}/chunks",
    response_model=UploadChunkResponse,
    summary="上传文件块",
    description="上传文件的分块数据"
)
async def upload_chunk(
    task_id: str = Path(..., description="任务ID"),
    request: UploadChunkRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """上传文件块"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 转换请求为DTO
        input_dto = UploadChunkInputDTO(
            tenant_id=tenant_id,
            task_id=task_id,
            file_id=request.file_id,
            chunk_number=request.chunk_number,
            chunk_data=request.chunk_data,
            chunk_size=request.chunk_size,
            start_byte=request.start_byte,
            end_byte=request.end_byte,
            is_final_chunk=request.is_final_chunk,
            minio_bucket=request.minio_bucket,
            minio_object_name=request.minio_object_name,
            checksum_md5=request.checksum_md5,
            checksum_sha256=request.checksum_sha256,
            max_retries=request.max_retries
        )
        
        # 调用服务层
        response_dto = await upload_service.upload_chunk(input_dto)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "上传文件块失败"
            )
        
        # 转换为正确的响应类型
        return UploadChunkResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data,
            next_chunk=getattr(response_dto, 'next_chunk', None),
            progress=getattr(response_dto, 'progress', None),
            is_completed=getattr(response_dto, 'is_completed', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件块失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传文件块失败: {str(e)}"
        )


@router.post(
    "/{task_id}/complete",
    response_model=CompleteUploadResponse,
    summary="完成文件上传",
    description="完成文件上传并进行完整性校验"
)
async def complete_upload(
    task_id: str = Path(..., description="任务ID"),
    request: CompleteUploadRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """完成文件上传"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 转换请求为DTO
        input_dto = CompleteUploadInputDTO(
            task_id=task_id,
            file_id=request.file_id,
            checksum_md5=request.checksum_md5,
            checksum_sha256=request.checksum_sha256
        )
        
        # 调用服务层
        response_dto = await upload_service.complete_upload(input_dto)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "完成文件上传失败"
            )
        
        return CompleteUploadResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完成文件上传失败: {str(e)}"
        )


@router.post(
    "/{task_id}/resume",
    response_model=ResumeUploadResponse,
    summary="断点续传",
    description="恢复中断的上传任务"
)
async def resume_upload(
    task_id: str = Path(..., description="任务ID"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """断点续传"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 创建恢复上传的 DTO
        input_dto = ResumeUploadInputDTO(
            task_id=task_id,
            tenant_id=tenant_id,
            created_by=user_id
        )
        
        # 调用服务层
        response_dto = await upload_service.resume_upload(input_dto)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "恢复上传失败"
            )
        
        return ResumeUploadResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data,
            resumed_files=getattr(response_dto, 'resumed_files', None),
            total_files_to_resume=getattr(response_dto, 'total_files_to_resume', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复上传失败: {str(e)}"
        )


@router.get(
    "/{task_id}",
    response_model=GetUploadTaskResponse,
    summary="获取上传任务详情",
    description="根据任务ID获取上传任务详细信息"
)
async def get_upload_task(
    task_id: str = Path(..., description="任务ID"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取上传任务详情"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 调用服务层
        response_dto = await upload_service.get_upload_task(task_id, tenant_id)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=response_dto.errors[0].message if response_dto.errors else "上传任务不存在"
            )
        
        return GetUploadTaskResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传任务失败: {str(e)}"
        )


@router.get(
    "/",
    response_model=ListUploadTasksResponse,
    summary="获取上传任务列表",
    description="获取上传任务列表，支持分页、筛选和排序"
)
async def list_upload_tasks(
    task_id: Optional[str] = Query(None, description="任务ID"),
    created_by: Optional[str] = Query(None, description="创建者"),
    status: Optional[Status] = Query(None, description="任务状态"),  # 使用正确的枚举类型
    proc_status: Optional[UploadProcStatusEnum] = Query(None, description="处理状态"),
    source_type: Optional[UploadSourceTypeEnum] = Query(None, description="源类型"),
    tags: Optional[List[str]] = Query(None, description="标签"),
    category: Optional[str] = Query(None, description="分类"),
    created_at_start: Optional[str] = Query(None, description="创建时间开始"),
    created_at_end: Optional[str] = Query(None, description="创建时间结束"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取上传任务列表"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 转换查询参数为DTO
        query_dto = UploadTaskQueryDTO(
            tenant_id=tenant_id,
            task_id=task_id,
            created_by=created_by,
            status=status,
            proc_status=proc_status,
            source_type=source_type,
            tags=tags,
            category=category,
            created_at_start=created_at_start,
            created_at_end=created_at_end
        )
        
        # 构建分页参数
        pagination = PaginationParams(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 调用服务层
        response_dto = await upload_service.list_upload_tasks(query_dto, pagination)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "获取上传任务列表失败"
            )
        
        return ListUploadTasksResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data,
            pagination=getattr(response_dto, 'pagination', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传任务列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传任务列表失败: {str(e)}"
        )


@router.get(
    "/{task_id}/files",
    response_model=ListUploadTaskFilesResponse,
    summary="获取任务文件列表",
    description="获取上传任务中的文件列表"
)
async def list_upload_task_files(
    task_id: str = Path(..., description="任务ID"),
    file_id: Optional[str] = Query(None, description="文件ID"),
    proc_status: Optional[UploadProcStatusEnum] = Query(None, description="处理状态"),
    file_type: Optional[FileTypeEnum] = Query(None, description="文件类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页大小"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: str = Query("asc", description="排序方向"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取任务文件列表"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 转换查询参数为DTO
        query_dto = UploadTaskFileQueryDTO(
            tenant_id=tenant_id,
            task_id=task_id,
            file_id=file_id,
            proc_status=proc_status,
            file_type=file_type
        )
        
        # 构建分页参数
        pagination = PaginationParams(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 调用服务层
        response_dto = await upload_service.list_upload_task_files(query_dto, pagination)
        
        if not response_dto.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response_dto.errors[0].message if response_dto.errors else "获取任务文件列表失败"
            )
        
        return ListUploadTaskFilesResponse(
            success=response_dto.success,
            errors=response_dto.errors,
            data=response_dto.data,
            pagination=getattr(response_dto, 'pagination', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务文件列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务文件列表失败: {str(e)}"
        )


@router.get(
    "/{task_id}/progress",
    response_model=UploadProgressResponse,
    summary="获取上传进度",
    description="获取上传任务的进度信息"
)
async def get_upload_progress(
    task_id: str = Path(..., description="任务ID"),
    include_file_details: bool = Query(False, description="是否包含文件详情"),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取上传进度"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 调用服务层获取进度
        progress_dto = await upload_service.get_upload_progress(task_id, tenant_id, include_file_details)
        
        if not progress_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="进度信息不存在"
            )
        
        # 转换为响应格式
        return UploadProgressResponse(
            success=True,
            data=progress_dto
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传进度失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传进度失败: {str(e)}"
        )


@router.get(
    "/statistics/overview",
    response_model=UploadTaskStatsResponse,
    summary="获取上传任务统计概览",
    description="获取上传任务的总体统计信息"
)
async def get_upload_task_stats(
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant)
):
    """获取上传任务统计信息"""
    try:
        service_manager = get_service_manager()
        upload_service = service_manager.upload_task_service
        
        # 调用服务层 - 需要实现此方法
        stats_dto = await upload_service.get_upload_task_stats(tenant_id, user_id)
        
        return UploadTaskStatsResponse(
            success=True,
            data=stats_dto
        )
        
    except Exception as e:
        logger.error(f"获取上传任务统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传任务统计失败: {str(e)}"
        )