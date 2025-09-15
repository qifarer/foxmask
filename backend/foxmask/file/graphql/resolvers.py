# -*- coding: utf-8 -*-
# foxmask/file/graphql/resolvers.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# GraphQL resolvers for file metadata management

import base64
from typing import Any, Dict, List, Optional

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from foxmask.core.config import settings
from foxmask.file.models import File, FileChunk, FileStatus, FileType as FileTypeModel, FileVisibility
from foxmask.file.services import file_service
from foxmask.utils.helpers import get_current_time

from .schemas import (
    ChunkStatusEnum,
    ChunkUploadInput,
    ChunkUploadResponse,
    ChunkUploadResult,
    CompleteUploadInput,
    Error,
    FileChunkListResponse,
    FileChunkListResult,
    FileChunkResponse,
    FileChunkType,
    FileCreateInput,
    FileListResponse,
    FileListResult,
    FileResponse,
    FileStatsResponse,
    FileStatusEnum,
    FileType,
    FileTypeEnum,
    FileUpdateInput,
    FileVisibilityEnum,
    MultipartUploadResponse,
    MultipartUploadResult,
    PresignedUrlResponse,
    SuccessResponse,
    UploadProgress,
    UploadProgressResponse,
)

# 日志配置
import logging
logger = logging.getLogger(__name__)

# 转换函数
def file_to_gql(file: File) -> FileType:
    """将数据库 File 模型转换为 GraphQL FileType"""
    return FileType.from_model(file)

def chunk_to_gql(chunk: FileChunk) -> FileChunkType:
    """将数据库 FileChunk 模型转换为 GraphQL FileChunkType"""
    return FileChunkType.from_model(chunk)

# 错误处理函数
def handle_error(message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict] = None) -> Error:
    """创建标准错误响应"""
    logger.error(f"Error {code}: {message}. Details: {details}")
    return Error(message=message, code=code, details=details)

# 权限检查函数
def check_file_permission(file: File, context: Dict, require_owner: bool = False) -> bool:
    """
    检查用户对文件的访问权限
    
    Args:
        file: 文件对象
        context: 请求上下文
        require_owner: 是否要求文件所有者权限
    
    Returns:
        bool: 是否有权限访问
    """
    user_id = context.get("user_id")
    user_roles = context.get("roles", [])
    
    # 文件所有者有完全权限
    if file.uploaded_by == user_id:
        return True
    
    # 如果要求必须是所有者（如删除操作）
    if require_owner:
        return False
    
    # 使用模型的权限检查方法
    return file.can_be_accessed_by(user_id, user_roles)

# Query 定义
@strawberry.type
class FileQuery:
    """文件查询操作"""
    
    @strawberry.field
    async def health(self) -> str:
        """健康检查端点"""
        return "OK"
    
    @strawberry.field
    async def file(self, info: Info, file_id: strawberry.ID) -> FileResponse:
        """根据ID获取单个文件"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to file endpoint")
            return FileResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )

        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context):
                logger.warning(f"User {user_id} lacks permission to access file {file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            logger.info(f"File {file_id} retrieved successfully by user {user_id}")
            return FileResponse(
                success=True,
                file=file_to_gql(file)
            )
        except Exception as e:
            logger.exception(f"Failed to get file {file_id}: {str(e)}")
            return FileResponse(
                success=False,
                error=handle_error(f"Failed to get file: {str(e)}", "GET_FILE_ERROR")
            )
    
    @strawberry.field
    async def files(
        self, 
        info: Info, 
        page: int = 1,
        page_size: int = 10,
        status: Optional[FileStatusEnum] = None,
        visibility: Optional[FileVisibilityEnum] = None,
        file_type: Optional[FileTypeEnum] = None,
        tags: Optional[List[str]] = None
    ) -> FileListResponse:
        """分页获取文件列表"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to files endpoint")
            return FileListResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )

        try:
            # 转换枚举类型
            status_model = FileStatus[status.name] if status else None
            visibility_model = FileVisibility[visibility.name] if visibility else None
            file_type_model = FileTypeModel[file_type.name] if file_type else None
            
            files, total_count = await file_service.list_files(
                user_id=user_id,
                tenant_id=tenant_id,
                page=page,
                page_size=page_size,
                status=status_model,
                visibility=visibility_model,
                file_type=file_type_model,
                tags=tags
            )
            
            result = FileListResult(
                files=[file_to_gql(file) for file in files],
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=page * page_size < total_count,
                has_previous=page > 1
            )
            
            logger.info(f"Listed {len(files)} files for user {user_id}, page {page}")
            return FileListResponse(
                success=True,
                result=result
            )
        except Exception as e:
            logger.exception(f"Failed to list files: {str(e)}")
            return FileListResponse(
                success=False,
                error=handle_error(f"Failed to list files: {str(e)}", "LIST_FILES_ERROR")
            )
    
    @strawberry.field
    async def file_chunks(
        self,
        info: Info,
        file_id: strawberry.ID,
        page: int = 1,
        page_size: int = 50
    ) -> FileChunkListResponse:
        """获取文件的分块信息"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to file_chunks endpoint")
            return FileChunkListResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return FileChunkListResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return FileChunkListResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context, require_owner=True):
                logger.warning(f"User {user_id} lacks permission to access chunks of file {file_id}")
                return FileChunkListResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file's chunks", "FORBIDDEN")
                )
            
            # 分页查询 chunks
            chunks = await file_service.get_file_chunks(str(file_id), page, page_size)
            total_count = await file_service.count_file_chunks(str(file_id))
            
            result = FileChunkListResult(
                chunks=[chunk_to_gql(chunk) for chunk in chunks],
                total_count=total_count,
                file_id=str(file_id),
                upload_id=file.upload_id or ""
            )
            
            logger.info(f"Retrieved {len(chunks)} chunks for file {file_id}")
            return FileChunkListResponse(
                success=True,
                result=result
            )
        except Exception as e:
            logger.exception(f"Failed to get file chunks for file {file_id}: {str(e)}")
            return FileChunkListResponse(
                success=False,
                error=handle_error(f"Failed to get file chunks: {str(e)}", "GET_CHUNKS_ERROR")
            )
    
    @strawberry.field
    async def upload_progress(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> UploadProgressResponse:
        """获取文件上传进度"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to upload_progress endpoint")
            return UploadProgressResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return UploadProgressResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return UploadProgressResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context, require_owner=True):
                logger.warning(f"User {user_id} lacks permission to access upload progress of file {file_id}")
                return UploadProgressResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file's upload progress", "FORBIDDEN")
                )
            
            progress = await file_service.get_upload_progress(str(file_id))
            upload_progress = UploadProgress(
                file_id=progress["file_id"],
                filename=progress["filename"],
                status=FileStatusEnum(progress["status"].value),
                uploaded_chunks=progress["uploaded_chunks"],
                total_chunks=progress["total_chunks"],
                progress_percentage=progress["progress_percentage"]
            )
            
            logger.info(f"Retrieved upload progress for file {file_id}: {progress['progress_percentage']}%")
            return UploadProgressResponse(
                success=True,
                progress=upload_progress
            )
        except Exception as e:
            logger.exception(f"Failed to get upload progress for file {file_id}: {str(e)}")
            return UploadProgressResponse(
                success=False,
                error=handle_error(f"Failed to get upload progress: {str(e)}", "UPLOAD_PROGRESS_ERROR")
            )

    @strawberry.field
    async def file_stats(self, info: Info) -> FileStatsResponse:
        """获取用户文件统计信息"""
        context = info.context
        user_id = context.get("user_id")
        
        if not user_id:
            logger.warning("Unauthorized access attempt to file_stats endpoint")
            return FileStatsResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            stats = await file_service.get_user_files_stats(user_id)
            logger.info(f"Retrieved file stats for user {user_id}")
            return FileStatsResponse(
                success=True,
                stats=stats
            )
        except Exception as e:
            logger.exception(f"Failed to get file stats for user {user_id}: {str(e)}")
            return FileStatsResponse(
                success=False,
                error=handle_error(f"Failed to get file stats: {str(e)}", "FILE_STATS_ERROR")
            )
    
    @strawberry.field
    async def presigned_download_url(
        self,
        info: Info,
        file_id: strawberry.ID,
        expires: int = 3600
    ) -> PresignedUrlResponse:
        """获取预签名下载URL"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to presigned_download_url endpoint")
            return PresignedUrlResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return PresignedUrlResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return PresignedUrlResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context):
                logger.warning(f"User {user_id} lacks permission to access file {file_id}")
                return PresignedUrlResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            url = await file_service.get_presigned_download_url(str(file_id), expires)
            if not url:
                logger.error(f"Failed to generate download URL for file {file_id}")
                return PresignedUrlResponse(
                    success=False,
                    error=handle_error("Failed to generate download URL", "URL_GENERATION_ERROR")
                )
            
            logger.info(f"Generated presigned URL for file {file_id}, expires in {expires} seconds")
            return PresignedUrlResponse(
                success=True,
                url=url
            )
        except Exception as e:
            logger.exception(f"Failed to generate download URL for file {file_id}: {str(e)}")
            return PresignedUrlResponse(
                success=False,
                error=handle_error(f"Failed to generate download URL: {str(e)}", "URL_GENERATION_ERROR")
            )

# Mutation 定义
@strawberry.type
class FileMutation:
    """文件变更操作"""
    
    @strawberry.mutation
    async def create_file(
        self, 
        info: Info, 
        file_data: FileCreateInput
    ) -> FileResponse:
        """创建新文件记录"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to create_file endpoint")
            return FileResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        # 转换输入数据
        file_dict = {
            "filename": file_data.filename,
            "file_size": file_data.file_size,
            "content_type": file_data.content_type,
            "description": file_data.description,
            "tags": file_data.tags or [],
            "visibility": file_data.visibility.value if file_data.visibility else FileVisibilityEnum.PRIVATE.value,
            "allowed_users": file_data.allowed_users or [],
            "allowed_roles": file_data.allowed_roles or [],
            "metadata": file_data.metadata or {},
            "is_multipart": file_data.is_multipart,
            "chunk_size": file_data.chunk_size
        }
        
        try:
            file = await file_service.create_file(file_dict, user_id, tenant_id)
            logger.info(f"Created file {file.id} by user {user_id}")
            return FileResponse(
                success=True,
                file=file_to_gql(file)
            )
        except Exception as e:
            logger.exception(f"Failed to create file: {str(e)}")
            return FileResponse(
                success=False,
                error=handle_error(f"Failed to create file: {str(e)}", "CREATE_FILE_ERROR")
            )
    
    @strawberry.mutation
    async def update_file(
        self, 
        info: Info, 
        file_id: strawberry.ID,
        update_data: FileUpdateInput
    ) -> FileResponse:
        """更新文件信息"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to update_file endpoint")
            return FileResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to update this file", "FORBIDDEN")
                )
            
            # 只有文件所有者可以更新
            if file.uploaded_by != user_id:
                logger.warning(f"User {user_id} is not owner of file {file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to update this file", "FORBIDDEN")
                )
            
            update_dict = {}
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.tags is not None:
                update_dict["tags"] = update_data.tags
            if update_data.visibility is not None:
                update_dict["visibility"] = FileVisibility[update_data.visibility.name]
            if update_data.allowed_users is not None:
                update_dict["allowed_users"] = update_data.allowed_users
            if update_data.allowed_roles is not None:
                update_dict["allowed_roles"] = update_data.allowed_roles
            if update_data.metadata is not None:
                update_dict["metadata"] = update_data.metadata
            
            updated_metadata = await file_service.update_file(str(file_id), update_dict)
            if not updated_metadata:
                logger.error(f"File not found after update: {file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("File not found after update", "FILE_NOT_FOUND")
                )
            
            logger.info(f"Updated file {file_id} by user {user_id}")
            return FileResponse(
                success=True,
                file=file_to_gql(updated_metadata)
            )
        except Exception as e:
            logger.exception(f"Failed to update file {file_id}: {str(e)}")
            return FileResponse(
                success=False,
                error=handle_error(f"Failed to update file: {str(e)}", "UPDATE_FILE_ERROR")
            )
    
    @strawberry.mutation
    async def delete_file(
        self, 
        info: Info, 
        file_id: strawberry.ID
    ) -> SuccessResponse:
        """删除文件"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to delete_file endpoint")
            return SuccessResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to delete this file", "FORBIDDEN")
                )
            
            # 只有文件所有者可以删除
            if file.uploaded_by != user_id:
                logger.warning(f"User {user_id} is not owner of file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to delete this file", "FORBIDDEN")
                )
            
            success = await file_service.delete_file(str(file_id))
            if not success:
                logger.error(f"Failed to delete file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Failed to delete file", "DELETE_FILE_ERROR")
                )
            
            logger.info(f"Deleted file {file_id} by user {user_id}")
            return SuccessResponse(
                success=True,
                message="File deleted successfully"
            )
        except Exception as e:
            logger.exception(f"Failed to delete file {file_id}: {str(e)}")
            return SuccessResponse(
                success=False,
                error=handle_error(f"Failed to delete file: {str(e)}", "DELETE_FILE_ERROR")
            )
    
    @strawberry.mutation
    async def init_upload(
        self,
        info: Info,
        file_data: FileCreateInput
    ) -> MultipartUploadResponse:
        """初始化分块上传"""
        context = info.context
        logger.debug(f"Context in init_upload: {context}")
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to init_upload endpoint")
            return MultipartUploadResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        file_dict = {
            "filename": file_data.filename,
            "file_size": file_data.file_size,
            "content_type": file_data.content_type,
            "description": file_data.description,
            "tags": file_data.tags or [],
            "visibility": file_data.visibility.value if file_data.visibility else FileVisibilityEnum.PRIVATE.value,
            "allowed_users": file_data.allowed_users or [],
            "allowed_roles": file_data.allowed_roles or [],
            "metadata": file_data.metadata or {},
            "chunk_size": file_data.chunk_size
        }
        
        try:
            result = await file_service.init_multipart_upload(file_dict, user_id, tenant_id)
            logger.info(f"Initialized multipart upload for file {result['file_id']} by user {user_id}")
            return MultipartUploadResponse(
                success=True,
                result=MultipartUploadResult(
                    file_id=result["file_id"],
                    upload_id=result["upload_id"],
                    chunk_size=result["chunk_size"],
                    total_chunks=result["total_chunks"],
                    chunk_urls=result["chunk_urls"],
                    minio_bucket=result["minio_bucket"]
                )
            )
        except Exception as e:
            logger.exception(f"Failed to initialize upload: {str(e)}")
            return MultipartUploadResponse(
                success=False,
                error=handle_error(f"Failed to initialize upload: {str(e)}", "INIT_UPLOAD_ERROR")
            )
    
    @strawberry.mutation
    async def upload_chunk(
        self,
        info: Info,
        chunk_data: ChunkUploadInput
    ) -> ChunkUploadResponse:
        """上传文件分块"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to upload_chunk endpoint")
            return ChunkUploadResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(chunk_data.file_id))
            if not file or file.uploaded_by != user_id:
                logger.warning(f"User {user_id} not authorized to upload to file {chunk_data.file_id}")
                return ChunkUploadResponse(
                    success=False,
                    error=handle_error("Not authorized to upload to this file", "FORBIDDEN")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {chunk_data.file_id}: expected {tenant_id}, got {file.tenant_id}")
                return ChunkUploadResponse(
                    success=False,
                    error=handle_error("Not authorized to upload to this file", "FORBIDDEN")
                )
            
            chunk_content = base64.b64decode(chunk_data.chunk_data)
            
            if len(chunk_content) != chunk_data.chunk_size:
                logger.warning(f"Chunk size mismatch for file {chunk_data.file_id}: expected {chunk_data.chunk_size}, got {len(chunk_content)}")
                return ChunkUploadResponse(
                    success=False,
                    error=handle_error(
                        f"Chunk size mismatch: expected {chunk_data.chunk_size}, got {len(chunk_content)}",
                        "CHUNK_SIZE_MISMATCH"
                    )
                )
            
            result = await file_service.upload_chunk(
                file_id=str(chunk_data.file_id),
                upload_id=chunk_data.upload_id,
                chunk_number=chunk_data.chunk_number,
                chunk_data=chunk_content,
                chunk_size=chunk_data.chunk_size,
                checksum_md5=chunk_data.checksum_md5,
                checksum_sha256=chunk_data.checksum_sha256
            )
            
            logger.info(f"Uploaded chunk {chunk_data.chunk_number} for file {chunk_data.file_id}")
            return ChunkUploadResponse(
                success=True,
                result=ChunkUploadResult(
                    file_id=chunk_data.file_id,
                    upload_id=chunk_data.upload_id,
                    chunk_number=result["chunk_number"],
                    minio_etag=result["etag"],
                    status=ChunkStatusEnum.UPLOADED
                )
            )
        except Exception as e:
            logger.exception(f"Failed to upload chunk {chunk_data.chunk_number} for file {chunk_data.file_id}: {str(e)}")
            return ChunkUploadResponse(
                success=False,
                error=handle_error(f"Failed to upload chunk: {str(e)}", "UPLOAD_CHUNK_ERROR")
            )
    
    @strawberry.mutation
    async def complete_upload(
        self,
        info: Info,
        complete_data: CompleteUploadInput
    ) -> FileResponse:
        """完成分块上传"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to complete_upload endpoint")
            return FileResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(complete_data.file_id))
            if not file or file.uploaded_by != user_id:
                logger.warning(f"User {user_id} not authorized to complete upload for file {complete_data.file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to complete this upload", "FORBIDDEN")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {complete_data.file_id}: expected {tenant_id}, got {file.tenant_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("Not authorized to complete this upload", "FORBIDDEN")
                )
            
            etags_dict = {etag.chunk_number: etag.etag for etag in complete_data.chunk_etags}
            file = await file_service.complete_multipart_upload(
                file_id=str(complete_data.file_id),
                upload_id=complete_data.upload_id,
                chunk_etags=etags_dict,
                checksum_md5=complete_data.checksum_md5,
                checksum_sha256=complete_data.checksum_sha256
            )
            
            if not file:
                logger.error(f"File not found after upload completion: {complete_data.file_id}")
                return FileResponse(
                    success=False,
                    error=handle_error("File not found after upload completion", "FILE_NOT_FOUND")
                )
            
            logger.info(f"Completed multipart upload for file {complete_data.file_id}")
            return FileResponse(
                success=True,
                file=file_to_gql(file)
            )
        except Exception as e:
            logger.exception(f"Failed to complete upload for file {complete_data.file_id}: {str(e)}")
            return FileResponse(
                success=False,
                error=handle_error(f"Failed to complete upload: {str(e)}", "COMPLETE_UPLOAD_ERROR")
            )
    
    @strawberry.mutation
    async def abort_upload(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> SuccessResponse:
        """中止分块上传"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to abort_upload endpoint")
            return SuccessResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file or file.uploaded_by != user_id:
                logger.warning(f"User {user_id} not authorized to abort upload for file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to abort this upload", "FORBIDDEN")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to abort this upload", "FORBIDDEN")
                )
            
            success = await file_service.abort_multipart_upload(str(file_id))
            if not success:
                logger.error(f"Failed to abort upload for file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Failed to abort upload", "ABORT_UPLOAD_ERROR")
                )
            
            logger.info(f"Aborted upload for file {file_id}")
            return SuccessResponse(
                success=True,
                message="Upload aborted successfully"
            )
        except Exception as e:
            logger.exception(f"Failed to abort upload for file {file_id}: {str(e)}")
            return SuccessResponse(
                success=False,
                error=handle_error(f"Failed to abort upload: {str(e)}", "ABORT_UPLOAD_ERROR")
            )
    
    @strawberry.mutation
    async def resume_upload(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> MultipartUploadResponse:
        """恢复分块上传"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to resume_upload endpoint")
            return MultipartUploadResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file or file.uploaded_by != user_id:
                logger.warning(f"User {user_id} not authorized to resume upload for file {file_id}")
                return MultipartUploadResponse(
                    success=False,
                    error=handle_error("Not authorized to resume this upload", "FORBIDDEN")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return MultipartUploadResponse(
                    success=False,
                    error=handle_error("Not authorized to resume this upload", "FORBIDDEN")
                )
            
            result = await file_service.resume_multipart_upload(str(file_id))
            logger.info(f"Resumed upload for file {file_id}")
            return MultipartUploadResponse(
                success=True,
                result=MultipartUploadResult(
                    file_id=result["file_id"],
                    upload_id=result["upload_id"],
                    chunk_size=result["chunk_size"],
                    total_chunks=result["total_chunks"],
                    chunk_urls=result["chunk_urls"],
                    minio_bucket=result["minio_bucket"]
                )
            )
        except Exception as e:
            logger.exception(f"Failed to resume upload for file {file_id}: {str(e)}")
            return MultipartUploadResponse(
                success=False,
                error=handle_error(f"Failed to resume upload: {str(e)}", "RESUME_UPLOAD_ERROR")
            )
    
    @strawberry.mutation
    async def increment_download_count(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> SuccessResponse:
        """增加文件下载计数"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to increment_download_count endpoint")
            return SuccessResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context):
                logger.warning(f"User {user_id} lacks permission to access file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            success = await file_service.increment_download_count(str(file_id))
            if not success:
                logger.error(f"Failed to increment download count for file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Failed to increment download count", "INCREMENT_DOWNLOAD_ERROR")
                )
            
            logger.info(f"Incremented download count for file {file_id}")
            return SuccessResponse(
                success=True,
                message="Download count incremented"
            )
        except Exception as e:
            logger.exception(f"Failed to increment download count for file {file_id}: {str(e)}")
            return SuccessResponse(
                success=False,
                error=handle_error(f"Failed to increment download count: {str(e)}", "INCREMENT_DOWNLOAD_ERROR")
            )
    
    @strawberry.mutation
    async def increment_view_count(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> SuccessResponse:
        """增加文件查看计数"""
        context = info.context
        user_id = context.get("user_id")
        tenant_id = context.get("tenant_id", settings.DEFAULT_TENANT_ID)
        
        if not user_id:
            logger.warning("Unauthorized access attempt to increment_view_count endpoint")
            return SuccessResponse(
                success=False,
                error=handle_error("Unauthorized: User ID not found", "UNAUTHORIZED")
            )
        
        try:
            file = await file_service.get_file(str(file_id))
            if not file:
                logger.warning(f"File not found: {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("File not found", "FILE_NOT_FOUND")
                )
            
            # 检查租户权限
            if file.tenant_id != tenant_id:
                logger.warning(f"Tenant mismatch for file {file_id}: expected {tenant_id}, got {file.tenant_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            if not check_file_permission(file, context):
                logger.warning(f"User {user_id} lacks permission to access file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Not authorized to access this file", "FORBIDDEN")
                )
            
            success = await file_service.increment_view_count(str(file_id))
            if not success:
                logger.error(f"Failed to increment view count for file {file_id}")
                return SuccessResponse(
                    success=False,
                    error=handle_error("Failed to increment view count", "INCREMENT_VIEW_ERROR")
                )
            
            logger.info(f"Incremented view count for file {file_id}")
            return SuccessResponse(
                success=True,
                message="View count incremented"
            )
        except Exception as e:
            logger.exception(f"Failed to increment view count for file {file_id}: {str(e)}")
            return SuccessResponse(
                success=False,
                error=handle_error(f"Failed to increment view count: {str(e)}", "INCREMENT_VIEW_ERROR")
            )