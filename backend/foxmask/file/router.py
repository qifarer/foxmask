from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
import json
from bson import ObjectId
from datetime import datetime

from .services import file_service
from .schemas import (
    FileUploadInitRequest, FileUploadInitResponse, ChunkUploadRequest, ChunkUploadResponse,
    FileCompleteUploadRequest, UploadProgressResponse, ResumeUploadResponse, FileResponse,
    FileListResponse, FileUpdateRequest, FileProcessingJobResponse, ErrorResponse, SuccessResponse,
    FileStatus, FileVisibility
)
from foxmask.shared.dependencies import get_user_from_token,get_chunk_upload_request
from foxmask.core.logger import logger
from foxmask.core.config import settings
from foxmask.utils.helpers import convert_objectids_to_strings

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload/init", response_model=FileUploadInitResponse)
async def init_file_upload(
    upload_request: FileUploadInitRequest,
    context: Dict = Depends(get_user_from_token)
):
    logger.warning("init_file_upload Call: start", extra={"request_id": "auto-generated"})
    """Initialize multipart file upload (requires write permission)"""
    try:
        result = await file_service.init_multipart_upload(
            upload_request, 
            context["user_id"],
            context.get("tenant_id", "default")
        )
        
        # 确保返回的是Pydantic模型实例，而不是字典
        if isinstance(result, dict):
            return FileUploadInitResponse(**result)
        return result
        
    except Exception as e:
        logger.error(f"Failed to initialize file upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize upload: {str(e)}"
        )
    

@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_file_chunk(
    upload_request: ChunkUploadRequest = Depends(get_chunk_upload_request),
    file: UploadFile = File(...),
    context: Dict = Depends(get_user_from_token)
):
    print("upload_file_chunk Call: start")
    
    """Upload a file chunk (requires write permission)"""
    # 验证文件所有权
    file_metadata = await file_service.get_file_metadata(upload_request.file_id)
    if not file_metadata or file_metadata.uploaded_by != context["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload to this file"
        )
    
    # Read chunk data
    chunk_data = await file.read()
    print(f"upload_request:, {upload_request.model_dump}")
    # 验证块大小是否匹配
    if len(chunk_data) != upload_request.chunk_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk size mismatch: expected {upload_request.chunk_size}, got {len(chunk_data)}"
        )
    
    print(f"chunk_data:, {chunk_data}")
    try:
        result = await file_service.upload_chunk(
            file_id=upload_request.file_id,
            upload_id=upload_request.upload_id,
            chunk_number=upload_request.chunk_number,
            chunk_data=chunk_data,
            chunk_size=upload_request.chunk_size,
            checksum_md5=upload_request.checksum_md5,
            checksum_sha256=upload_request.checksum_sha256
        )
        
        # 确保返回的是Pydantic模型实例
        if isinstance(result, dict):
            return ChunkUploadResponse(**result)
        return result
        
    except Exception as e:
        logger.error(f"Failed to upload chunk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {str(e)}"
        )
    

        
@router.post("/upload/complete", response_model=FileResponse)
async def complete_file_upload(
    complete_request: FileCompleteUploadRequest,
    context: Dict = Depends(get_user_from_token)
):
    """Complete multipart file upload (requires write permission)"""
    # 验证文件所有权
    file_metadata = await file_service.get_file_metadata(complete_request.file_id)
    if not file_metadata or file_metadata.uploaded_by != context["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this upload"
        )
    
    try:
        file_metadata = await file_service.complete_multipart_upload(
            file_id=complete_request.file_id,
            upload_id=complete_request.upload_id,
            chunk_etags=complete_request.chunk_etags,
            checksum_md5=complete_request.checksum_md5,
            checksum_sha256=complete_request.checksum_sha256
        )
        #response_data = file_metadata.to_response_dict()
        #return FileResponse(**response_data)
        # 确保返回的是Pydantic模型实例
        if isinstance(file_metadata, dict):
            # 转换字典中的 ObjectId 为字符串
            file_metadata = convert_objectids_to_strings(file_metadata)
            return FileResponse(**file_metadata)
        else:
            # 如果是对象，转换为字典并处理 ObjectId
            file_dict = file_metadata.dict() if hasattr(file_metadata, 'dict') else file_metadata
            file_dict = convert_objectids_to_strings(file_dict)
            return FileResponse(**file_dict)
        
    except Exception as e:
        logger.error(f"Failed to complete upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}"
        )

@router.get("/{file_id}/upload/progress", response_model=UploadProgressResponse)
async def get_upload_progress(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get upload progress for a file (requires read permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    try:
        progress = await file_service.get_upload_progress(file_id)
        
        # 确保返回的是Pydantic模型实例
        if isinstance(progress, dict):
            return UploadProgressResponse(**progress)
        return progress
        
    except Exception as e:
        logger.error(f"Failed to get upload progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload progress: {str(e)}"
        )

@router.post("/{file_id}/upload/resume", response_model=ResumeUploadResponse)
async def resume_file_upload(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Resume a multipart file upload (requires write permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if file_metadata.uploaded_by != context["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    try:
        result = await file_service.resume_multipart_upload(file_id)
        
        # 确保返回的是Pydantic模型实例
        if isinstance(result, dict):
            return ResumeUploadResponse(**result)
        return result
        
    except Exception as e:
        logger.error(f"Failed to resume upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume upload: {str(e)}"
        )

@router.delete("/{file_id}/upload/abort")
async def abort_file_upload(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Abort a multipart file upload (requires write permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if file_metadata.uploaded_by != context["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    try:
        success = await file_service.abort_multipart_upload(file_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to abort upload")
        
        return {"message": "Upload aborted successfully"}
    except Exception as e:
        logger.error(f"Failed to abort upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to abort upload: {str(e)}"
        )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get file metadata (requires read permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission - 文件所有者或具有admin权限的API Key可以访问
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"] and
        file_metadata.visibility != FileVisibility.PUBLIC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this file"
        )
    
    # 确保返回的是Pydantic模型实例
    if isinstance(file_metadata, dict):
        return FileResponse(**file_metadata)
    return file_metadata

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get download URL for a file (requires read permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"] and
        file_metadata.visibility != FileVisibility.PUBLIC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this file"
        )
    
    # Generate presigned URL
    try:
        download_url = await file_service.get_presigned_download_url(file_id)
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        return {"download_url": download_url}
    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Delete a file (requires delete permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission - 只有文件所有者或具有admin权限的API Key可以删除
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this file"
        )
    
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
        
        return {"message": "File deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.get("/", response_model=FileListResponse)
async def list_files(
    context: Dict = Depends(get_user_from_token),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID (admin only)"),
    status: Optional[FileStatus] = Query(None, description="Filter by file status"),
    visibility: Optional[FileVisibility] = Query(None, description="Filter by visibility")
):
    """List files (requires read permission)"""
    # 如果是admin权限，可以查看所有文件或指定用户的文件
    if "admin" in context["permissions"] and user_id:
        target_user_id = user_id
    else:
        # 普通用户只能查看自己的文件
        target_user_id = context["user_id"]
    
    try:
        files, total_count = await file_service.list_files(
            user_id=target_user_id,
            page=page,
            page_size=page_size,
            status=status,
            visibility=visibility
        )
        
        return FileListResponse(
            files=files,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total_count
        )
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@router.put("/{file_id}", response_model=FileResponse)
async def update_file_metadata(
    file_id: str,
    update_request: FileUpdateRequest,
    context: Dict = Depends(get_user_from_token)
):
    """Update file metadata (requires write permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"]):
        raise HTTPException(status_code=403, detail="Not authorized to update this file")
    
    try:
        updated_metadata = await file_service.update_file_metadata(
            file_id, update_request
        )
        
        # 确保返回的是Pydantic模型实例
        if isinstance(updated_metadata, dict):
            return FileResponse(**updated_metadata)
        return updated_metadata
        
    except Exception as e:
        logger.error(f"Failed to update file metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file metadata: {str(e)}"
        )

@router.get("/stats/summary")
async def get_files_stats(
    context: Dict = Depends(get_user_from_token),
    user_id: Optional[str] = Query(None, description="User ID to get stats for (admin only)")
):
    """Get files statistics (requires read permission)"""
    target_user_id = context["user_id"]
    
    # 如果是admin，可以查看其他用户的统计信息
    if "admin" in context["permissions"] and user_id:
        target_user_id = user_id
    
    try:
        stats = await file_service.get_user_files_stats(target_user_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get file stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file stats: {str(e)}"
        )

@router.post("/{file_id}/process")
async def process_file(
    file_id: str,
    job_type: str = Form(...),
    parameters: str = Form(...),
    priority: int = Form(1),
    context: Dict = Depends(get_user_from_token)
):
    """Start file processing job (requires write permission)"""
    file_metadata = await file_service.get_file_metadata(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if (file_metadata.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"]):
        raise HTTPException(status_code=403, detail="Not authorized to process this file")
    
    try:
        # 解析JSON参数
        params_dict = json.loads(parameters)
        
        job = await file_service.start_processing_job(
            file_id=file_id,
            job_type=job_type,
            parameters=params_dict,
            priority=priority,
            user_id=context["user_id"]
        )
        
        # 确保返回的是Pydantic模型实例
        if isinstance(job, dict):
            return FileProcessingJobResponse(**job)
        return job
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON parameters")
    except Exception as e:
        logger.error(f"Failed to start processing job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start processing job: {str(e)}"
        )

@router.get("/jobs/{job_id}", response_model=FileProcessingJobResponse)
async def get_processing_job(
    job_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get processing job status (requires read permission)"""
    try:
        job = await file_service.get_processing_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify ownership
        file_metadata = await file_service.get_file_metadata(job.file_id)
        if (file_metadata.uploaded_by != context["user_id"] and 
            "admin" not in context["permissions"]):
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        # 确保返回的是Pydantic模型实例
        if isinstance(job, dict):
            return FileProcessingJobResponse(**job)
        return job
        
    except Exception as e:
        logger.error(f"Failed to get processing job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing job: {str(e)}"
        )