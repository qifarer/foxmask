from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from foxmask.core.enums import *
from foxmask.file.enums import *
from foxmask.utils.helpers import get_current_timestamp

# 基础响应DTO
@dataclass(frozen=False)
class ErrorDTO:
    message: str
    code: str
    field: Optional[str] = None
    
@dataclass(frozen=False)
class BaseResponseDTO:
    success: bool
    errors: Optional[List["ErrorDTO"]] = None

# 分页DTO
@dataclass(frozen=False)
class PaginationParams:
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"

@dataclass(frozen=False)
class PageInfoDTO:
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int] = None
    current_page: int = 1
    total_pages: Optional[int] = None

# Entity DTOs - 修正字段名以匹配Entity
@dataclass(frozen=False)
class UploadTaskFileChunkDTO:
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
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING  # ✅ 移除Optional

@dataclass(frozen=False)
class UploadTaskFileDTO:
    uid: str
    tenant_id: str
    master_id: str
    original_path: str
    storage_path: str
    filename: str
    file_size: int
    file_type: FileTypeEnum
    content_type: str
    extension: str
    minio_bucket: Optional[str] = None
    minio_object_name: Optional[str] = None
    minio_etag: Optional[str] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    total_chunks: int = 1  # ✅ 默认值改为1
    uploaded_chunks: int = 0
    current_chunk: int = 0
    progress: float = 0.0
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    extracted_metadata: Dict[str, Any] = field(default_factory=dict)  # ✅ 修正类型
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING  # ✅ 移除Optional
    chunks: Optional[List[UploadTaskFileChunkDTO]] = None

@dataclass(frozen=False)
class UploadTaskDTO:
    uid: str
    tenant_id: str
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_at: datetime = field(default_factory=get_current_timestamp)  # ✅ 修正默认值
    updated_at: datetime = field(default_factory=get_current_timestamp)  # ✅ 修正默认值
    archived_at: Optional[datetime] = None
    created_by: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    proc_meta: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING  # ✅ 移除Optional
    source_type: UploadSourceTypeEnum = UploadSourceTypeEnum.SINGLE_FILE
    source_paths: List[str] = field(default_factory=list)
    upload_strategy: UploadStrategyEnum = UploadStrategyEnum.SEQUENTIAL
    max_parallel_uploads: int = 5  # ✅ 修正默认值
    chunk_size: int = 10 * 1024 * 1024  # ✅ 修正默认值
    preserve_structure: bool = True  # ✅ 修正默认值
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = True  # ✅ 修正默认值
    file_type_filters: List[FileTypeEnum] = field(default_factory=list)
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
    files: Optional[List[UploadTaskFileDTO]] = None

# 输入 DTOs
@dataclass(frozen=False)
class InitializeUploadInputDTO:
    tenant_id: str  # ✅ 移除Optional
    created_by: str  # ✅ 移除Optional
    title: str
    source_type: UploadSourceTypeEnum
    source_paths: List[str]
    upload_strategy: UploadStrategyEnum = UploadStrategyEnum.SEQUENTIAL
    chunk_size: int = 10 * 1024 * 1024  # ✅ 添加默认值
    desc: Optional[str] = None
    max_parallel_uploads: int = 5  # ✅ 修正默认值
    preserve_structure: bool = True  # ✅ 修正默认值
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = True  # ✅ 修正默认值
    file_type_filters: List[FileTypeEnum] = field(default_factory=list)
    max_file_size: Optional[int] = None
    files: Optional[List["InitializeUploadFileInputDTO"]] = None
    resume_task_id: Optional[str] = None

@dataclass(frozen=False)
class InitializeUploadFileInputDTO:
    original_path: str
    filename: str
    file_size: int
    file_type: FileTypeEnum
    content_type: str
    extension: str
    chunk_size: int

@dataclass(frozen=False)
class UploadChunkInputDTO:
    tenant_id: str  # ✅ 移除Optional
    task_id: str
    file_id: str
    chunk_number: int
    chunk_data: str
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    max_retries: int = 3

@dataclass(frozen=False)
class CompleteUploadInputDTO:
    task_id: str
    file_id: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None

# 查询和过滤 DTOs
@dataclass(frozen=False)
class UploadTaskQueryDTO:
    tenant_id: str
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    status: Optional[Status] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    source_type: Optional[UploadSourceTypeEnum] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    created_at_start: Optional[datetime] = None
    created_at_end: Optional[datetime] = None

@dataclass(frozen=False)
class UploadTaskFileQueryDTO:
    tenant_id: str
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    file_type: Optional[FileTypeEnum] = None

@dataclass(frozen=False)
class UploadTaskFileChunkQueryDTO:
    tenant_id: str
    file_id: Optional[str] = None
    chunk_number: Optional[int] = None
    proc_status: Optional[UploadProcStatusEnum] = None

# 更新 DTOs - 修正字段名以匹配Entity
@dataclass(frozen=False)
class UploadTaskUpdateDTO:
    title: Optional[str] = None
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

@dataclass(frozen=False)
class UploadTaskProgressUpdateDTO:
    discovered_files: Optional[int] = None
    processing_files: Optional[int] = None
    completed_files: Optional[int] = None
    failed_files: Optional[int] = None
    uploaded_size: Optional[int] = None
    total_files: Optional[int] = None
    total_size: Optional[int] = None
    discovery_started_at: Optional[datetime] = None
    discovery_completed_at: Optional[datetime] = None

@dataclass(frozen=False)
class UploadTaskFileUpdateDTO:
    proc_status: Optional[UploadProcStatusEnum] = None
    uploaded_chunks: Optional[int] = None
    current_chunk: Optional[int] = None
    progress: Optional[float] = None
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    minio_etag: Optional[str] = None  # ✅ 添加缺失字段
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None

# 响应 DTOs
@dataclass(frozen=False)
class InitializeUploadResponseDTO(BaseResponseDTO):
    data: Optional[UploadTaskDTO] = None

@dataclass(frozen=False)
class UploadChunkResponseDTO(BaseResponseDTO):
    data: Optional[UploadTaskFileChunkDTO] = None
    next_chunk: Optional[int] = None
    progress: Optional[float] = None
    is_completed: Optional[bool] = None

@dataclass(frozen=False)
class CompleteUploadResponseDTO(BaseResponseDTO):
    data: Optional[UploadTaskFileDTO] = None

@dataclass(frozen=False)
class GetUploadTaskResponseDTO(BaseResponseDTO):
    data: Optional[UploadTaskDTO] = None

@dataclass(frozen=False)
class ListUploadTasksResponseDTO(BaseResponseDTO):
    data: Optional[List[UploadTaskDTO]] = None
    pagination: Optional[PageInfoDTO] = None

@dataclass(frozen=False)
class ListUploadTaskFilesResponseDTO(BaseResponseDTO):
    data: Optional[List[UploadTaskFileDTO]] = None
    pagination: Optional[PageInfoDTO] = None

@dataclass(frozen=False)
class ListUploadTaskFileChunksResponseDTO(BaseResponseDTO):
    data: Optional[List[UploadTaskFileChunkDTO]] = None
    pagination: Optional[PageInfoDTO] = None

# 断点续传 DTOs
@dataclass(frozen=False)
class ResumeUploadInputDTO:
    task_id: str
    tenant_id: str
    created_by: str

@dataclass(frozen=False)
class ResumeUploadResponseDTO(BaseResponseDTO):
    data: Optional[UploadTaskDTO] = None
    resumed_files: Optional[List[str]] = None
    total_files_to_resume: int = 0

@dataclass(frozen=False)
class UploadResumeInfoDTO:
    task_id: str
    file_id: str
    uploaded_chunks: int
    total_chunks: int
    next_chunk_number: int
    file_size: int
    uploaded_size: int
    progress: float

# 进度监控 DTOs - 修复字段顺序
@dataclass(frozen=False)
class UploadProgressDTO:
    task_id: str
    total_files: int
    completed_files: int
    failed_files: int
    progress_percentage: float  # ✅ 没有默认值的字段在前
    uploaded_size: int
    total_size: int
    processing_files: int = 0  # ✅ 有默认值的字段在后
    average_upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_uploading_files: Optional[List[str]] = None

@dataclass(frozen=False)
class FileUploadProgressDTO:
    file_id: str
    filename: str
    progress: float
    uploaded_chunks: int
    total_chunks: int
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_chunk: Optional[int] = None

@dataclass(frozen=False)
class UploadTaskStatsDTO:
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_files: int
    total_size: int
    uploaded_size: int = 0
    average_upload_speed: Optional[float] = None
    success_rate: float = 0.0

@dataclass(frozen=False)
class ProgressQueryDTO:
    task_id: str
    tenant_id: str
    include_file_details: bool = False