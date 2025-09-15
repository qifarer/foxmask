# -*- coding: utf-8 -*-
# foxmask/file/graphql/schemas.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# GraphQL schema definitions for file metadata management

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import strawberry
from strawberry.scalars import JSON


# ===== Enum 定义 =====
@strawberry.enum
class FileStatusEnum(Enum):
    """文件状态枚举"""
    DRAFT = "draft"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELED = "canceled"


@strawberry.enum
class FileVisibilityEnum(Enum):
    """文件可见性枚举"""
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"


@strawberry.enum
class FileTypeEnum(Enum):
    """文件类型枚举"""
    PDF = "pdf"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    VECTOR = "vector"
    AUDIO = "audio"
    VIDEO = "video"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    ARCHIVE = "archive"
    BINARY = "binary"
    UNKNOWN = "unknown"


@strawberry.enum
class ChunkStatusEnum(Enum):
    """分片状态枚举"""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    FAILED = "failed"


# ===== 类型定义 =====
@strawberry.type
class FileType:
    """文件类型 GraphQL 类型"""
    id: strawberry.ID
    filename: str
    file_size: int
    content_type: str
    file_type: FileTypeEnum
    extension: str
    url: Optional[str]
    minio_bucket: str
    minio_object_name: str
    status: FileStatusEnum
    upload_progress: float
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    uploaded_by: str
    tenant_id: str
    visibility: FileVisibilityEnum
    allowed_users: List[str]
    allowed_roles: List[str]
    tags: List[str]
    description: Optional[str]
    metadata: JSON
    is_multipart: bool
    upload_id: Optional[str]
    chunk_size: int
    total_chunks: int
    uploaded_chunks: int
    verified_chunks: int
    created_at: str
    updated_at: str
    uploaded_at: Optional[str]
    processed_at: Optional[str]
    expires_at: Optional[str]
    download_count: int
    view_count: int
    last_downloaded_at: Optional[str]
    last_viewed_at: Optional[str]

    @classmethod
    def from_model(cls, file) -> 'FileType':
        """将 File 模型转换为 GraphQL 类型"""
        return cls(
            id=strawberry.ID(str(file.id)),
            filename=file.filename,
            file_size=file.file_size,
            content_type=file.content_type,
            file_type=FileTypeEnum(file.file_type.value),
            extension=file.extension,
            url=file.url,
            minio_bucket=file.minio_bucket,
            minio_object_name=file.minio_object_name,
            status=FileStatusEnum(file.status.value),
            upload_progress=file.upload_progress,
            checksum_md5=file.checksum_md5,
            checksum_sha256=file.checksum_sha256,
            uploaded_by=file.uploaded_by,
            tenant_id=file.tenant_id,
            visibility=FileVisibilityEnum(file.visibility.value),
            allowed_users=file.allowed_users,
            allowed_roles=file.allowed_roles,
            tags=file.tags,
            description=file.description,
            metadata=file.metadata,
            is_multipart=file.is_multipart,
            upload_id=file.upload_id,
            chunk_size=file.chunk_size,
            total_chunks=file.total_chunks,
            uploaded_chunks=file.uploaded_chunks,
            verified_chunks=file.verified_chunks,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat(),
            uploaded_at=file.uploaded_at.isoformat() if file.uploaded_at else None,
            processed_at=file.processed_at.isoformat() if file.processed_at else None,
            expires_at=file.expires_at.isoformat() if file.expires_at else None,
            download_count=file.download_count,
            view_count=file.view_count,
            last_downloaded_at=file.last_downloaded_at.isoformat() if file.last_downloaded_at else None,
            last_viewed_at=file.last_viewed_at.isoformat() if file.last_viewed_at else None
        )


@strawberry.type
class FileChunkType:
    """文件分片类型 GraphQL 类型"""
    id: strawberry.ID
    file_id: str
    upload_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    minio_object_name: str
    minio_bucket: str
    minio_etag: Optional[str]
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    status: ChunkStatusEnum
    retry_count: int
    created_at: str
    uploaded_at: Optional[str]
    verified_at: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_model(cls, chunk) -> 'FileChunkType':
        """将 FileChunk 模型转换为 GraphQL 类型"""
        return cls(
            id=strawberry.ID(str(chunk.id)),
            file_id=chunk.file_id,
            upload_id=chunk.upload_id,
            chunk_number=chunk.chunk_number,
            chunk_size=chunk.chunk_size,
            start_byte=chunk.start_byte,
            end_byte=chunk.end_byte,
            minio_object_name=chunk.minio_object_name,
            minio_bucket=chunk.minio_bucket,
            minio_etag=chunk.minio_etag,
            checksum_md5=chunk.checksum_md5,
            checksum_sha256=chunk.checksum_sha256,
            status=ChunkStatusEnum(chunk.status.value),
            retry_count=chunk.retry_count,
            created_at=chunk.created_at.isoformat(),
            uploaded_at=chunk.uploaded_at.isoformat() if chunk.uploaded_at else None,
            verified_at=chunk.verified_at.isoformat() if chunk.verified_at else None,
            error_message=chunk.error_message
        )


# ===== 输入类型 =====
@strawberry.input
class FileCreateInput:
    """文件创建输入类型"""
    filename: str
    file_size: int
    content_type: str = "application/octet-stream"
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[FileVisibilityEnum] = FileVisibilityEnum.PRIVATE
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None
    is_multipart: Optional[bool] = False
    chunk_size: Optional[int] = 5 * 1024 * 1024  # 5MB


@strawberry.input
class FileUpdateInput:
    """文件更新输入类型"""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[FileVisibilityEnum] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None


@strawberry.input
class ChunkEtagInput:
    """分片ETag输入类型"""
    chunk_number: int
    etag: str


@strawberry.input
class ChunkUploadInput:
    """分片上传输入类型"""
    file_id: strawberry.ID
    upload_id: str
    chunk_number: int
    chunk_size: int
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    chunk_data: str  # Base64编码的分片数据


@strawberry.input
class CompleteUploadInput:
    """完成上传输入类型"""
    file_id: strawberry.ID
    upload_id: str
    chunk_etags: List[ChunkEtagInput]
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None


# ===== 响应类型 =====
@strawberry.type
class UploadProgress:
    """上传进度类型"""
    file_id: str
    filename: str
    status: FileStatusEnum
    uploaded_chunks: int
    total_chunks: int
    progress_percentage: float


@strawberry.type
class MultipartUploadResult:
    """分片上传结果类型"""
    file_id: str
    upload_id: str
    chunk_size: int
    total_chunks: int
    chunk_urls: JSON
    minio_bucket: str


@strawberry.type
class ChunkUploadResult:
    """分片上传结果类型"""
    file_id: str
    upload_id: str
    chunk_number: int
    minio_etag: str
    status: ChunkStatusEnum


@strawberry.type
class Error:
    """错误响应类型"""
    message: str
    code: str
    details: Optional[JSON] = None


@strawberry.type
class FileResponse:
    """文件响应类型"""
    success: bool
    message: Optional[str] = None
    file: Optional[FileType] = None
    error: Optional[Error] = None


@strawberry.type
class FileListResult:
    """文件列表结果类型"""
    files: List[FileType]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


@strawberry.type
class FileListResponse:
    """文件列表响应类型"""
    success: bool
    message: Optional[str] = None
    result: Optional[FileListResult] = None
    error: Optional[Error] = None


@strawberry.type
class FileChunkResponse:
    """文件分片响应类型"""
    success: bool
    message: Optional[str] = None
    chunk: Optional[FileChunkType] = None
    error: Optional[Error] = None


@strawberry.type
class FileChunkListResult:
    """文件分片列表结果类型"""
    chunks: List[FileChunkType]
    total_count: int
    file_id: str
    upload_id: str


@strawberry.type
class FileChunkListResponse:
    """文件分片列表响应类型"""
    success: bool
    message: Optional[str] = None
    result: Optional[FileChunkListResult] = None
    error: Optional[Error] = None


@strawberry.type
class UploadProgressResponse:
    """上传进度响应类型"""
    success: bool
    message: Optional[str] = None
    progress: Optional[UploadProgress] = None
    error: Optional[Error] = None


@strawberry.type
class MultipartUploadResponse:
    """分片上传响应类型"""
    success: bool
    message: Optional[str] = None
    result: Optional[MultipartUploadResult] = None
    error: Optional[Error] = None


@strawberry.type
class ChunkUploadResponse:
    """分片上传响应类型"""
    success: bool
    message: Optional[str] = None
    result: Optional[ChunkUploadResult] = None
    error: Optional[Error] = None


@strawberry.type
class FileStatsResponse:
    """文件统计响应类型"""
    success: bool
    message: Optional[str] = None
    stats: Optional[JSON] = None
    error: Optional[Error] = None


@strawberry.type
class PresignedUrlResponse:
    """预签名URL响应类型"""
    success: bool
    message: Optional[str] = None
    url: Optional[str] = None
    error: Optional[Error] = None


@strawberry.type
class SuccessResponse:
    """成功响应类型"""
    success: bool
    message: Optional[str] = None
    error: Optional[Error] = None