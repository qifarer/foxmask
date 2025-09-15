# -*- coding: utf-8 -*-
# foxmask/file/router.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import  Optional, Dict
from ..services import file_service
from .schemas import (
    FileUploadInitRequest, FileUploadInitResponse, ChunkUploadRequest, ChunkUploadResponse,
    FileCompleteUploadRequest, ResumeUploadResponse, FileResponse,
    FileListResponse, FileUpdateRequest, FileStatus, FileVisibility
)
from foxmask.shared.dependencies import get_user_from_token, get_chunk_upload_request
from foxmask.utils.helpers import convert_objectids_to_strings
from foxmask.core.logger import logger

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload/init", response_model=FileUploadInitResponse)
async def init_file_upload(
    upload_request: FileUploadInitRequest,
    context: Dict = Depends(get_user_from_token)
    ):
    """Initialize multipart file upload (requires write permission)"""
    logger.info("init_file_upload: Starting file upload initialization")
    
    try:
        result = await file_service.init_multipart_upload(
            upload_request, 
            context["user_id"],
            context.get("tenant_id", "default")
        )
        # Ensure response is Pydantic model instance
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

    """Upload a file chunk (requires write permission)"""
    logger.info(f"upload_file_chunk: Uploading chunk {upload_request.chunk_number} for file {upload_request.file_id}")
    
    # Verify file ownership
    file = await file_service.get_file(upload_request.file_id)
    if not file or file.uploaded_by != context["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to upload to this file"
        )
    
    # Read chunk data
    chunk_data = await file.read()
    
    # Validate chunk size
    if len(chunk_data) != upload_request.chunk_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk size mismatch: expected {upload_request.chunk_size}, got {len(chunk_data)}"
        )

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
        
        # Ensure response is Pydantic model instance
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
    logger.info(f"complete_file_upload: Completing upload for file {complete_request.file_id}")
    
    # Verify file ownership
    file = await file_service.get_file(complete_request.file_id)
    if not file or file.uploaded_by != context["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this upload"
        )
    
    try:
        file = await file_service.complete_multipart_upload(
            file_id=complete_request.file_id,
            upload_id=complete_request.upload_id,
            chunk_etags=complete_request.chunk_etags,
            checksum_md5=complete_request.checksum_md5,
            checksum_sha256=complete_request.checksum_sha256
        )
        
        # Convert ObjectId to string and ensure Pydantic model response
        if isinstance(file, dict):
            file = convert_objectids_to_strings(file)
            return FileResponse(**file)
        else:
            file_dict = file.dict() if hasattr(file, 'dict') else file
            file_dict = convert_objectids_to_strings(file_dict)
            return FileResponse(**file_dict)
        
    except Exception as e:
        logger.error(f"Failed to complete upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}"
        )

@router.post("/{file_id}/upload/resume", response_model=ResumeUploadResponse)
async def resume_file_upload(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Resume a multipart file upload (requires write permission)"""
    logger.info(f"resume_file_upload: Resuming upload for file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if file.uploaded_by != context["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    try:
        result = await file_service.resume_multipart_upload(file_id)
        
        # Ensure response is Pydantic model instance
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
    logger.info(f"abort_file_upload: Aborting upload for file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if file.uploaded_by != context["user_id"]:
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
async def get_file(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get file metadata (requires read permission)"""
    logger.info(f"get_file: Fetching metadata for file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission - file owner or admin can access
    if (file.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"] and
        file.visibility != FileVisibility.PUBLIC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this file"
        )
    
    # Ensure response is Pydantic model instance
    if isinstance(file, dict):
        return FileResponse(**file)
    return file


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    context: Dict = Depends(get_user_from_token)
):
    """Get download URL for a file (requires read permission)"""
    logger.info(f"download_file: Generating download URL for file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission
    if (file.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"] and
        file.visibility != FileVisibility.PUBLIC):
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
    logger.info(f"delete_file: Deleting file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permission - only file owner or admin can delete
    if (file.uploaded_by != context["user_id"] and 
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
    file_status: Optional[FileStatus] = Query(None, description="Filter by file status"),
    visibility: Optional[FileVisibility] = Query(None, description="Filter by visibility")
):
    """List files (requires read permission)"""
    logger.info(f"list_files: Listing files for user {context['user_id']} with filters - page: {page}, page_size: {page_size}, user_id: {user_id}, status: {status}, visibility: {visibility}")
    # Admin can view all files or specific user's files
    if "admin" in context["permissions"] and user_id:
        target_user_id = user_id
    else:
        # Regular users can only view their own files
        target_user_id = context["user_id"]
    
    try:
        files, total_count = await file_service.list_files(
            user_id=target_user_id,
            page=page,
            page_size=page_size,
            status=file_status,
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
async def update_file(
    file_id: str,
    update_request: FileUpdateRequest,
    context: Dict = Depends(get_user_from_token)
):
    """Update file metadata (requires write permission)"""
    logger.info(f"update_file: Updating metadata for file {file_id}")
    
    file = await file_service.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify ownership
    if (file.uploaded_by != context["user_id"] and 
        "admin" not in context["permissions"]):
        raise HTTPException(status_code=403, detail="Not authorized to update this file")
    
    try:
        updated_metadata = await file_service.update_file(
            file_id, update_request
        )
        
        # Ensure response is Pydantic model instance
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
    logger.info(f"get_files_stats: Getting file stats for user {context['user_id']} with target user {user_id}")
    
    target_user_id = context["user_id"]
    
    # Admin can view other users' statistics
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
