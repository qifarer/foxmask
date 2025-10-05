# foxmask/file/api/schemas/upload.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from .base import BaseResponse, PageInfoSchema

# 枚举类型
class UploadProcStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadSourceTypeEnum(str, Enum):
    SINGLE_FILE = "single_file"
    MULTIPLE_FILES = "multiple_files"
    DIRECTORY = "directory"

class UploadStrategyEnum(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

class FileTypeEnum(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    OTHER = "other"

class Status(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"

# 实体 schemas
class UploadTaskFileChunkSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    uid: str
    tenant_id: str
    master_id: str
    file_id: str
    chunk_number: int = Field(ge=0)
    chunk_size: int = Field(ge=0)
    start_byte: int = Field(ge=0)
    end_byte: int = Field(ge=0)
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    minio_etag: Optional[str] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: Optional[UploadProcStatusEnum] = UploadProcStatusEnum.PENDING

class UploadTaskFileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    uid: str
    tenant_id: str
    master_id: str
    original_path: str
    storage_path: str
    filename: str
    file_size: int = Field(ge=0)
    file_type: FileTypeEnum
    content_type: str
    extension: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    total_chunks: int = Field(default=0, ge=0)
    uploaded_chunks: int = Field(default=0, ge=0)
    current_chunk: int = Field(default=0, ge=0)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    upload_speed: Optional[float] = Field(default=None, ge=0.0)
    estimated_time_remaining: Optional[float] = Field(default=None, ge=0.0)
    extracted_metadata: Optional[Dict[str, Any]] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: Optional[UploadProcStatusEnum] = UploadProcStatusEnum.PENDING
    chunks: Optional[List[UploadTaskFileChunkSchema]] = None

class UploadTaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    uid: str
    tenant_id: str
    title: str = Field(..., min_length=1)
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    archived_at: Optional[datetime] = None
    created_by: Optional[str] = None
    allowed_users: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    proc_meta: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    proc_status: Optional[UploadProcStatusEnum] = UploadProcStatusEnum.PENDING
    source_type: UploadSourceTypeEnum = UploadSourceTypeEnum.SINGLE_FILE
    source_paths: List[str] = Field(default_factory=list)
    upload_strategy: UploadStrategyEnum = UploadStrategyEnum.SEQUENTIAL
    max_parallel_uploads: int = Field(default=2, ge=1)
    chunk_size: int = Field(default=5*1024*1024, ge=1024)
    preserve_structure: bool = False
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = False
    file_type_filters: List[FileTypeEnum] = Field(default_factory=list)
    max_file_size: Optional[int] = Field(default=None, ge=0)
    discovered_files: int = Field(default=0, ge=0)
    processing_files: int = Field(default=0, ge=0)
    total_files: int = Field(default=0, ge=0)
    completed_files: int = Field(default=0, ge=0)
    failed_files: int = Field(default=0, ge=0)
    total_size: int = Field(default=0, ge=0)
    uploaded_size: int = Field(default=0, ge=0)
    discovery_started_at: Optional[datetime] = None
    discovery_completed_at: Optional[datetime] = None
    files: Optional[List[UploadTaskFileSchema]] = None

# 输入 schemas
class InitializeUploadFileInputSchema(BaseModel):
    original_path: str
    filename: str = Field(..., min_length=1)
    file_size: int = Field(..., ge=0)
    file_type: FileTypeEnum
    content_type: str
    extension: str
    chunk_size: int = Field(..., ge=1024)

# 请求 schemas (用于 API 端点)
class InitializeUploadRequest(BaseModel):
    title: str = Field(..., min_length=1)
    source_type: UploadSourceTypeEnum
    source_paths: List[str] = Field(..., min_items=1)
    upload_strategy: UploadStrategyEnum
    chunk_size: int = Field(..., ge=1024)
    desc: Optional[str] = None
    max_parallel_uploads: int = Field(default=1, ge=1)
    preserve_structure: bool = False
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = False
    file_type_filters: List[FileTypeEnum] = Field(default_factory=list)
    max_file_size: Optional[int] = Field(default=None, ge=0)
    files: Optional[List[InitializeUploadFileInputSchema]] = None
    resume_task_id: Optional[str] = None

class UploadChunkRequest(BaseModel):
    file_id: str
    chunk_number: int = Field(..., ge=0)
    chunk_data: bytes = Field(..., min_length=1)
    chunk_size: int = Field(..., ge=1)
    start_byte: int = Field(..., ge=0)
    end_byte: int = Field(..., ge=0)
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    max_retries: int = Field(default=3, ge=0)

class CompleteUploadRequest(BaseModel):
    file_id: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None

# 更新请求 schemas
class UploadTaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    proc_meta: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class UploadTaskFileUpdateRequest(BaseModel):
    proc_status: Optional[UploadProcStatusEnum] = None
    uploaded_chunks: Optional[int] = Field(default=None, ge=0)
    current_chunk: Optional[int] = Field(default=None, ge=0)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    upload_speed: Optional[float] = Field(default=None, ge=0.0)
    estimated_time_remaining: Optional[float] = Field(default=None, ge=0.0)
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None

# 查询参数 schemas
class UploadTaskQueryParams(BaseModel):
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    status: Optional[str] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    source_type: Optional[UploadSourceTypeEnum] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    created_at_start: Optional[datetime] = None
    created_at_end: Optional[datetime] = None

class UploadTaskFileQueryParams(BaseModel):
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    file_type: Optional[FileTypeEnum] = None

# 响应 schemas
class InitializeUploadResponse(BaseResponse):
    data: Optional[UploadTaskSchema] = None

class UploadChunkResponse(BaseResponse):
    data: Optional[UploadTaskFileChunkSchema] = None
    next_chunk: Optional[int] = Field(default=None, ge=0)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    is_completed: Optional[bool] = None

class CompleteUploadResponse(BaseResponse):
    data: Optional[UploadTaskFileSchema] = None

class GetUploadTaskResponse(BaseResponse):
    data: Optional[UploadTaskSchema] = None

class ListUploadTasksResponse(BaseResponse):
    data: Optional[List[UploadTaskSchema]] = None
    pagination: Optional[PageInfoSchema] = None  # 使用 PageInfoSchema 而不是 PaginationParams

class ListUploadTaskFilesResponse(BaseResponse):
    data: Optional[List[UploadTaskFileSchema]] = None
    pagination: Optional[PageInfoSchema] = None

class ResumeUploadResponse(BaseResponse):
    data: Optional[UploadTaskSchema] = None
    resumed_files: Optional[List[str]] = None
    total_files_to_resume: int = Field(default=0, ge=0)

# 进度监控 schemas
class UploadProgressSchema(BaseModel):
    task_id: str
    total_files: int = Field(ge=0)
    completed_files: int = Field(ge=0)
    failed_files: int = Field(ge=0)
    progress_percentage: float = Field(ge=0.0, le=100.0)
    uploaded_size: int = Field(ge=0)
    total_size: int = Field(ge=0)
    average_upload_speed: Optional[float] = Field(default=None, ge=0.0)
    estimated_time_remaining: Optional[float] = Field(default=None, ge=0.0)
    current_uploading_files: Optional[List[str]] = None

class FileUploadProgressSchema(BaseModel):
    file_id: str
    filename: str
    progress: float = Field(ge=0.0, le=100.0)
    uploaded_chunks: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    upload_speed: Optional[float] = Field(default=None, ge=0.0)
    estimated_time_remaining: Optional[float] = Field(default=None, ge=0.0)
    current_chunk: Optional[int] = Field(default=None, ge=0)

class UploadTaskStatsSchema(BaseModel):
    total_tasks: int = Field(ge=0)
    active_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    failed_tasks: int = Field(ge=0)
    total_files: int = Field(ge=0)
    total_size: int = Field(ge=0)
    average_upload_speed: Optional[float] = Field(default=None, ge=0.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=100.0)

class UploadResumeInfoSchema(BaseModel):
    task_id: str
    file_id: str
    uploaded_chunks: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    next_chunk_number: int = Field(ge=0)
    file_size: int = Field(ge=0)
    uploaded_size: int = Field(ge=0)
    progress: float = Field(ge=0.0, le=100.0)

class UploadProgressResponse(BaseResponse):
    data: Optional[UploadProgressSchema] = None

class UploadTaskStatsResponse(BaseResponse):
    data: Optional[UploadTaskStatsSchema] = None

# 兼容性 schemas (保持与现有代码兼容)
UploadTaskCreateRequest = InitializeUploadRequest
UploadTaskResponse = UploadTaskSchema
UploadTaskListResponse = ListUploadTasksResponse
UploadTaskFileCreateRequest = InitializeUploadFileInputSchema
UploadTaskFileResponse = UploadTaskFileSchema
UploadTaskFileListResponse = ListUploadTaskFilesResponse