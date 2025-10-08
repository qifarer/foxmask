from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from foxmask.core.enums import Status, Visibility
from foxmask.file.enums import (
    FileTypeEnum, 
    UploadProcStatusEnum, 
    UploadSourceTypeEnum, 
    UploadStrategyEnum
)
from foxmask.utils.helpers import get_current_timestamp


# ============================
# 基础响应 DTO
# ============================

@dataclass(frozen=False)
class ErrorDTO:
    """错误信息数据传输对象"""
    message: str
    code: str
    field: Optional[str] = None


@dataclass(frozen=False)
class BaseResponseDTO:
    """基础响应数据传输对象"""
    success: bool
    errors: Optional[List[ErrorDTO]] = None


# ============================
# 分页 DTO
# ============================

@dataclass(frozen=False)
class PaginationParams:
    """分页参数数据传输对象"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"


@dataclass(frozen=False)
class PageInfoDTO:
    """分页信息数据传输对象"""
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int] = None
    current_page: int = 1
    total_pages: Optional[int] = None


# ============================
# 实体 DTO
# ============================

@dataclass(frozen=False)
class UploadTaskFileChunkDTO:
    """上传任务文件分块数据传输对象"""
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
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING


@dataclass(frozen=False)
class UploadTaskFileDTO:
    """上传任务文件数据传输对象"""
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
    total_chunks: int = 1
    uploaded_chunks: int = 0
    current_chunk: int = 0
    progress: float = 0.0
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    extracted_metadata: Dict[str, Any] = field(default_factory=dict)
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING
    chunks: Optional[List[UploadTaskFileChunkDTO]] = None


@dataclass(frozen=False)
class UploadTaskDTO:
    """上传任务数据传输对象"""
    uid: str
    tenant_id: str
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_at: datetime = field(default_factory=get_current_timestamp)
    updated_at: datetime = field(default_factory=get_current_timestamp)
    archived_at: Optional[datetime] = None
    created_by: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    proc_meta: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    proc_status: UploadProcStatusEnum = UploadProcStatusEnum.PENDING
    source_type: UploadSourceTypeEnum = UploadSourceTypeEnum.SINGLE_FILE
    source_paths: List[str] = field(default_factory=list)
    upload_strategy: UploadStrategyEnum = UploadStrategyEnum.SEQUENTIAL
    max_parallel_uploads: int = 5
    chunk_size: int = 10 * 1024 * 1024
    preserve_structure: bool = True
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = True
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


# ============================
# 输入 DTO
# ============================

@dataclass(frozen=False)
class InitializeUploadInputDTO:
    """初始化上传输入数据传输对象"""
    tenant_id: str
    created_by: str
    title: str
    source_type: UploadSourceTypeEnum
    source_paths: List[str]
    upload_strategy: UploadStrategyEnum = UploadStrategyEnum.SEQUENTIAL
    chunk_size: int = 10 * 1024 * 1024
    desc: Optional[str] = None
    max_parallel_uploads: int = 5
    preserve_structure: bool = True
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = True
    file_type_filters: List[FileTypeEnum] = field(default_factory=list)
    max_file_size: Optional[int] = None
    files: Optional[List["InitializeUploadFileInputDTO"]] = None
    resume_task_id: Optional[str] = None


@dataclass(frozen=False)
class InitializeUploadFileInputDTO:
    """初始化上传文件输入数据传输对象"""
    original_path: str
    filename: str
    file_size: int
    file_type: FileTypeEnum
    content_type: str
    extension: str
    chunk_size: int


@dataclass(frozen=False)
class UploadChunkInputDTO:
    """上传分块输入数据传输对象"""
    tenant_id: str
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
    """完成上传输入数据传输对象"""
    task_id: str
    file_id: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None


# ============================
# 查询和过滤 DTO
# ============================

@dataclass(frozen=False)
class UploadTaskQueryDTO:
    """上传任务查询数据传输对象"""
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
    """上传任务文件查询数据传输对象"""
    tenant_id: str
    task_id: Optional[str] = None
    file_id: Optional[str] = None
    proc_status: Optional[UploadProcStatusEnum] = None
    file_type: Optional[FileTypeEnum] = None


@dataclass(frozen=False)
class UploadTaskFileChunkQueryDTO:
    """上传任务文件分块查询数据传输对象"""
    tenant_id: str
    file_id: Optional[str] = None
    chunk_number: Optional[int] = None
    proc_status: Optional[UploadProcStatusEnum] = None


# ============================
# 更新 DTO
# ============================

@dataclass(frozen=False)
class UploadTaskUpdateDTO:
    """上传任务更新数据传输对象"""
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
    """上传任务进度更新数据传输对象"""
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
    """上传任务文件更新数据传输对象"""
    proc_status: Optional[UploadProcStatusEnum] = None
    uploaded_chunks: Optional[int] = None
    current_chunk: Optional[int] = None
    progress: Optional[float] = None
    upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    minio_etag: Optional[str] = None
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    upload_started_at: Optional[datetime] = None
    upload_completed_at: Optional[datetime] = None
    note: Optional[str] = None


# ============================
# 响应 DTO
# ============================

@dataclass(frozen=False)
class InitializeUploadResponseDTO(BaseResponseDTO):
    """初始化上传响应数据传输对象"""
    data: Optional[UploadTaskDTO] = None


@dataclass(frozen=False)
class UploadChunkResponseDTO(BaseResponseDTO):
    """上传分块响应数据传输对象"""
    data: Optional[UploadTaskFileChunkDTO] = None
    next_chunk: Optional[int] = None
    progress: Optional[float] = None
    is_completed: Optional[bool] = None


@dataclass(frozen=False)
class CompleteUploadResponseDTO(BaseResponseDTO):
    """完成上传响应数据传输对象"""
    data: Optional[UploadTaskFileDTO] = None


@dataclass(frozen=False)
class GetUploadTaskResponseDTO(BaseResponseDTO):
    """获取上传任务响应数据传输对象"""
    data: Optional[UploadTaskDTO] = None


@dataclass(frozen=False)
class ListUploadTasksResponseDTO(BaseResponseDTO):
    """上传任务列表响应数据传输对象"""
    data: Optional[List[UploadTaskDTO]] = None
    pagination: Optional[PageInfoDTO] = None


@dataclass(frozen=False)
class ListUploadTaskFilesResponseDTO(BaseResponseDTO):
    """上传任务文件列表响应数据传输对象"""
    data: Optional[List[UploadTaskFileDTO]] = None
    pagination: Optional[PageInfoDTO] = None


@dataclass(frozen=False)
class ListUploadTaskFileChunksResponseDTO(BaseResponseDTO):
    """上传任务文件分块列表响应数据传输对象"""
    data: Optional[List[UploadTaskFileChunkDTO]] = None
    pagination: Optional[PageInfoDTO] = None


# ============================
# 断点续传 DTO
# ============================

@dataclass(frozen=False)
class ResumeUploadInputDTO:
    """恢复上传输入数据传输对象"""
    task_id: str
    tenant_id: str
    created_by: str


@dataclass(frozen=False)
class ResumeUploadResponseDTO(BaseResponseDTO):
    """恢复上传响应数据传输对象"""
    data: Optional[UploadTaskDTO] = None
    resumed_files: Optional[List[str]] = None
    total_files_to_resume: int = 0


@dataclass(frozen=False)
class UploadResumeInfoDTO:
    """上传恢复信息数据传输对象"""
    task_id: str
    file_id: str
    uploaded_chunks: int
    total_chunks: int
    next_chunk_number: int
    file_size: int
    uploaded_size: int
    progress: float


# ============================
# 进度监控 DTO
# ============================

@dataclass(frozen=False)
class UploadProgressDTO:
    """上传进度数据传输对象"""
    task_id: str
    total_files: int
    completed_files: int
    failed_files: int
    progress_percentage: float
    uploaded_size: int
    total_size: int
    processing_files: int = 0
    average_upload_speed: Optional[float] = None
    estimated_time_remaining: Optional[float] = None
    current_uploading_files: Optional[List[str]] = None


@dataclass(frozen=False)
class FileUploadProgressDTO:
    """文件上传进度数据传输对象"""
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
    """上传任务统计数据传输对象"""
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
    """进度查询数据传输对象"""
    task_id: str
    tenant_id: str
    include_file_details: bool = False