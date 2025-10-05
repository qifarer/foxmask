import strawberry
from typing import Optional, List
from strawberry.scalars import JSON
from strawberry.file_uploads import Upload
from datetime import datetime
from .enums import (
    FileTypeGql, 
    UploadProcStatusGql, 
    UploadSourceTypeGql, 
    UploadStrategyGql
)
from foxmask.core.schema import StatusEnum, VisibilityEnum, BaseResponse

# 基础类型
@strawberry.type
class Error:
    message: str
    code: str
    field: Optional[str] = None

@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int] = None
    current_page: int = 1
    total_pages: Optional[int] = None

@strawberry.input
class PaginationInput:
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"

# 实体类型
@strawberry.type
class UploadTaskFileChunk:
    uid: str
    tenant_id: str
    master_id: str
    file_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    minio_etag: Optional[str] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: UploadProcStatusGql = UploadProcStatusGql.PENDING

@strawberry.type
class UploadTaskFile:
    uid: str
    tenant_id: str
    master_id: str
    original_path: str
    storage_path: str
    filename: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    minio_bucket: str
    minio_object_name: str
    minio_etag: Optional[str] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    total_chunks: int = 0
    uploaded_chunks: int = 0
    current_chunk: int = 0
    progress: float = 0.0
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    extracted_metadata: Optional[JSON] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: UploadProcStatusGql = UploadProcStatusGql.PENDING
    chunks: Optional[List[UploadTaskFileChunk]] = None

@strawberry.type
class UploadTask:
    uid: str
    tenant_id: str
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: StatusEnum = StatusEnum.DRAFT
    visibility: VisibilityEnum = VisibilityEnum.PUBLIC
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    created_by: Optional[str] = None
    allowed_users: List[str] = strawberry.field(default_factory=list)  # 修复这里
    allowed_roles: List[str] = strawberry.field(default_factory=list)  # 修复这里
    proc_meta: Optional[JSON] = None
    error_info: Optional[JSON] = None
    metadata: Optional[JSON] = None
    proc_status: UploadProcStatusGql = UploadProcStatusGql.PENDING
    source_type: UploadSourceTypeGql = UploadSourceTypeGql.SINGLE_FILE
    source_paths: List[str] = strawberry.field(default_factory=list)  # 修复这里
    upload_strategy: UploadStrategyGql = UploadStrategyGql.SEQUENTIAL
    max_parallel_uploads: int = 2
    chunk_size: int = 5 * 1024 * 1024
    preserve_structure: bool = False
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = False
    file_type_filters: List[FileTypeGql] = strawberry.field(default_factory=list)  # 修复这里
    max_file_size: Optional[int] = None
    discovered_files: int = 0
    processing_files: int = 0
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    total_size: int = 0
    uploaded_size: int = 0
    discovery_started_at: Optional[datetime] = None
    discovery_completed_at: Optional[datetime] = None
    files: Optional[List["UploadTaskFile"]] = None

# 进度监控类型
@strawberry.type
class FileUploadProgress:
    file_id: str
    filename: str
    progress: float
    uploaded_chunks: int
    total_chunks: int
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_chunk: Optional[int] = None

@strawberry.type
class UploadProgress:
    task_id: str
    total_files: int
    completed_files: int
    failed_files: int
    progress_percentage: float
    uploaded_size: int
    total_size: int
    average_upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_uploading_files: Optional[List[FileUploadProgress]] = None

@strawberry.type
class UploadTaskStats:
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_files: int
    total_size: int
    average_upload_speed: Optional[float] = None
    success_rate: float = 0.0

@strawberry.type
class UploadResumeInfo:
    task_id: str
    file_id: str
    uploaded_chunks: int
    total_chunks: int
    next_chunk_number: int
    file_size: int
    uploaded_size: int
    progress: float

# 输入类型
@strawberry.input
class PaginationParams:
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"

@strawberry.input
class InitializeUploadInput:
    tenant_id: Optional[str] = None
    created_by: Optional[str] = None
    title: str
    source_type: UploadSourceTypeGql
    source_paths: List[str] = strawberry.field(default_factory=list)
    upload_strategy: UploadStrategyGql
    chunk_size: int
    desc: Optional[str] = None
    max_parallel_uploads: int = 1
    preserve_structure: bool = False
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = False
    file_type_filters: List[FileTypeGql] = strawberry.field(default_factory=list)
    max_file_size: Optional[int] = None
    files: Optional[List["InitializeUploadFileInput"]] = None
    resume_task_id: Optional[str] = None

@strawberry.input
class InitializeUploadFileInput:
    original_path: str
    filename: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    chunk_size: int

@strawberry.input
class UploadChunkInput:
    tenant_id: Optional[str] = None
    task_id: str
    file_id: str
    chunk_number: int
    chunk_data: Upload
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    max_retries: int = 3

@strawberry.input
class CompleteUploadInput:
    task_id: str
    file_id: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    force_complete: Optional[bool] = False

@strawberry.input
class ResumeUploadInput:
    task_id: str
    tenant_id: str
    created_by: str

# 查询和过滤输入类型
@strawberry.input
class UploadTaskQueryInput:
    tenant_id: str
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    status: Optional[StatusEnum] = None
    proc_status: Optional[UploadProcStatusGql] = None
    source_type: Optional[UploadSourceTypeGql] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    created_at_start: Optional[datetime] = None
    created_at_end: Optional[datetime] = None

@strawberry.input
class UploadTaskFileQueryInput:
    tenant_id: str
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    proc_status: Optional[UploadProcStatusGql] = None
    file_type: Optional[FileTypeGql] = None

@strawberry.input
class UploadTaskFileChunkQueryInput:
    tenant_id: str
    file_id: Optional[str] = None
    chunk_number: Optional[int] = None
    proc_status: Optional[UploadProcStatusGql] = None

@strawberry.input
class ProgressQueryInput:
    task_id: str
    tenant_id: str
    include_file_details: bool = False

# 更新输入类型
@strawberry.input
class UploadTaskUpdateInput:
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[StatusEnum] = None
    visibility: Optional[VisibilityEnum] = None
    proc_status: Optional[UploadProcStatusGql] = None
    proc_meta: Optional[JSON] = None
    error_info: Optional[JSON] = None
    metadata: Optional[JSON] = None

@strawberry.input
class UploadTaskProgressUpdateInput:
    discovered_files: Optional[int] = None
    processing_files: Optional[int] = None
    completed_files: Optional[int] = None
    failed_files: Optional[int] = None
    uploaded_size: Optional[int] = None
    total_files: Optional[int] = None
    total_size: Optional[int] = None
    discovery_started_at: Optional[datetime] = None
    discovery_completed_at: Optional[datetime] = None

@strawberry.input
class UploadTaskFileUpdateInput:
    proc_status: Optional[UploadProcStatusGql] = None
    uploaded_chunks: Optional[int] = None
    current_chunk: Optional[int] = None
    progress: Optional[float] = None
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    extracted_metadata: Optional[JSON] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None

# 响应类型
@strawberry.type
class InitializeUploadResponse(BaseResponse):
    data: Optional[UploadTask] = None

@strawberry.type
class UploadChunkResponse(BaseResponse):
    data: Optional[UploadTaskFileChunk] = None
    next_chunk: Optional[int] = None
    progress: Optional[float] = None
    is_completed: Optional[bool] = None

@strawberry.type
class CompleteUploadResponse(BaseResponse):
    data: Optional[UploadTaskFile] = None

@strawberry.type
class GetUploadTaskResponse(BaseResponse):
    data: Optional[UploadTask] = None

@strawberry.type
class ListUploadTasksResponse(BaseResponse):
    data: Optional[List[UploadTask]] = None
    pagination: Optional[PageInfo] = None

@strawberry.type
class ListUploadTaskFilesResponse(BaseResponse):
    data: Optional[List[UploadTaskFile]] = None
    pagination: Optional[PageInfo] = None

@strawberry.type
class ListUploadTaskFileChunksResponse(BaseResponse):
    data: Optional[List[UploadTaskFileChunk]] = None
    pagination: Optional[PageInfo] = None

@strawberry.type
class ResumeUploadResponse(BaseResponse):
    data: Optional[UploadTask] = None
    resumed_files: Optional[List[str]] = None
    total_files_to_resume: int = 0

@strawberry.type
class UploadProgressResponse(BaseResponse):
    data: Optional[UploadProgress] = None

@strawberry.type
class UploadTaskStatsResponse(BaseResponse):
    data: Optional[UploadTaskStats] = None

@strawberry.type
class UploadResumeInfoResponse(BaseResponse):
    data: Optional[UploadResumeInfo] = None