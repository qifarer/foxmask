from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import FileStatus, FileVisibility, FileType, ChunkStatus

# 基础配置
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

# 文件上传初始化请求
class FileUploadInitRequest(BaseSchema):
    """File upload initialization request"""
    
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_size: int = Field(..., ge=0, description="Total file size in bytes")
    content_type: str = Field(..., description="File content type")
    chunk_size: Optional[int] = Field(5 * 1024 * 1024, description="Chunk size in bytes", ge=1024 * 1024, le=100 * 1024 * 1024)
    description: Optional[str] = Field(None, max_length=1000, description="File description")
    tags: List[str] = Field(default_factory=list, description="File tags")
    visibility: FileVisibility = Field(FileVisibility.PRIVATE, description="File visibility level")
    allowed_users: List[str] = Field(default_factory=list, description="List of user IDs with access")
    allowed_roles: List[str] = Field(default_factory=list, description="List of roles with access")

# 文件上传初始化响应
class FileUploadInitResponse(BaseSchema):
    """File upload initialization response"""
    
    file_id: str = Field(..., description="File ID")
    upload_id: str = Field(..., description="MinIO upload ID")
    chunk_size: int = Field(..., description="Chunk size in bytes")
    total_chunks: int = Field(..., description="Total number of chunks")
    chunk_urls: Dict[int, str] = Field(..., description="Presigned URLs for each chunk")
    minio_bucket: str = Field(..., description="MinIO bucket name")

# 分块上传请求
class ChunkUploadRequest(BaseSchema):
    """Chunk upload request"""
    
    file_id: str = Field(..., description="File ID")
    upload_id: str = Field(..., description="Upload ID")
    chunk_number: int = Field(..., ge=1, description="Chunk number (1-based)")
    chunk_size: int = Field(..., ge=0, description="Chunk size in bytes")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")

# 分块上传响应
class ChunkUploadResponse(BaseSchema):
    """Chunk upload response"""
    
    chunk_number: int = Field(..., description="Chunk number")
    etag: str = Field(..., description="ETag of the uploaded chunk")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum of the uploaded chunk")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum of the uploaded chunk")
    chunk_size: int = Field(..., description="Actual chunk size")
    start_byte: int = Field(..., description="Start byte position")
    end_byte: int = Field(..., description="End byte position")

# 文件上传完成请求
class FileCompleteUploadRequest(BaseSchema):
    """File upload completion request"""
    
    file_id: str = Field(..., description="File ID")
    upload_id: str = Field(..., description="Upload ID")
    chunk_etags: Dict[int, str] = Field(..., description="ETags for all chunks")
    checksum_md5: Optional[str] = Field(None, description="Complete file MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="Complete file SHA256 checksum")

# 上传进度响应
class UploadProgressResponse(BaseSchema):
    """Upload progress response"""
    
    file_id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Filename")
    status: FileStatus = Field(..., description="Upload status")
    uploaded_chunks: int = Field(..., ge=0, description="Number of uploaded chunks")
    verified_chunks: int = Field(..., ge=0, description="Number of verified chunks")
    total_chunks: int = Field(..., ge=0, description="Total number of chunks")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Upload progress percentage")
    estimated_time_remaining: Optional[float] = Field(None, ge=0, description="Estimated time remaining in seconds")
    file_size: int = Field(..., description="Total file size in bytes")
    uploaded_size: int = Field(..., description="Total uploaded size in bytes")

# 分块状态响应
class ChunkStatusResponse(BaseSchema):
    """Chunk status response"""
    
    chunk_number: int = Field(..., description="Chunk number")
    status: ChunkStatus = Field(..., description="Chunk status")
    chunk_size: int = Field(..., description="Chunk size in bytes")
    start_byte: int = Field(..., description="Start byte position")
    end_byte: int = Field(..., description="End byte position")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")
    error_message: Optional[str] = Field(None, description="Error message if failed")

# 恢复上传响应
class ResumeUploadResponse(BaseSchema):
    """Resume upload response"""
    
    file_id: str = Field(..., description="File ID")
    upload_id: str = Field(..., description="Upload ID")
    filename: str = Field(..., description="Filename")
    status: FileStatus = Field(..., description="Current file status")
    missing_chunks: List[int] = Field(..., description="List of chunks that need to be uploaded")
    uploaded_chunks: List[int] = Field(..., description="List of already uploaded chunks")
    chunk_urls: Dict[int, str] = Field(..., description="Presigned URLs for missing chunks")
    total_chunks: int = Field(..., description="Total number of chunks")

# 文件信息响应
class FileResponse(BaseSchema):
    """File information response"""
    
    id: str = Field(..., description="File ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    file_type: FileType = Field(..., description="File type category")
    extension: str = Field(..., description="File extension")
    
    # MinIO 存储信息
    minio_bucket: str = Field(..., description="MinIO bucket name")
    minio_object_name: str = Field(..., description="MinIO object name")
    minio_url: Optional[str] = Field(None, description="MinIO access URL")
    
    # 状态管理
    status: FileStatus = Field(..., description="File status")
    upload_progress: float = Field(..., description="Upload progress percentage")
    
    # 校验信息
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")
    
    # 所有权和访问控制
    uploaded_by: str = Field(..., description="User ID who uploaded the file")
    tenant_id: str = Field(..., description="Tenant/organization ID")
    visibility: FileVisibility = Field(..., description="File visibility level")
    
    # 元数据
    tags: List[str] = Field(..., description="File tags")
    description: Optional[str] = Field(None, description="File description")
    
    # 时间戳
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    uploaded_at: Optional[datetime] = Field(None, description="Upload completion timestamp")
    
    # 统计信息
    download_count: int = Field(..., description="Number of downloads")
    view_count: int = Field(..., description="Number of views")

# 文件列表响应
class FileListResponse(BaseSchema):
    """File list response"""
    
    files: List[FileResponse] = Field(..., description="List of files")
    total_count: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of files per page")
    has_more: bool = Field(..., description="Whether there are more files")

# 文件更新请求
class FileUpdateRequest(BaseSchema):
    """File update request"""
    
    filename: Optional[str] = Field(None, min_length=1, max_length=255, description="New filename")
    description: Optional[str] = Field(None, max_length=1000, description="File description")
    tags: Optional[List[str]] = Field(None, description="File tags")
    visibility: Optional[FileVisibility] = Field(None, description="File visibility level")
    allowed_users: Optional[List[str]] = Field(None, description="List of user IDs with access")
    allowed_roles: Optional[List[str]] = Field(None, description="List of roles with access")

# 文件处理作业响应
class FileProcessingJobResponse(BaseSchema):
    """File processing job response"""
    
    job_id: str = Field(..., description="Job ID")
    file_id: str = Field(..., description="Target file ID")
    job_type: str = Field(..., description="Processing job type")
    status: str = Field(..., description="Job status")
    priority: int = Field(..., description="Job priority")
    parameters: Dict[str, Any] = Field(..., description="Processing parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing result")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(..., description="Number of retries")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

# 错误响应
class ErrorResponse(BaseSchema):
    """Error response"""
    
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")

# 成功响应
class SuccessResponse(BaseSchema):
    """Success response"""
    
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")