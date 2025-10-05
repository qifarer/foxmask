# foxmask/file/graphql/Gqls/upload.py
import strawberry
from typing import List, Optional
from datetime import datetime
from strawberry.file_uploads import Upload
from strawberry.scalars import JSON
from foxmask.core.schema import (
    VisibilityEnum,
    StatusEnum,
    BaseInput,
    BaseResponse,
    MutationResponse,
    QueryResponse
)

from .enums import (
    FileTypeGql,
    UploadTaskTypeGql,
    UploadSourceTypeGql,
    UploadStrategyGql,
    UploadProcStatusGql
)


@strawberry.type
class UploadTaskFileChunk:
    """文件分块类型"""
    id: str
    uid: str
    file_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    minio_etag: Optional[str]
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    retry_count: int
    max_retries: int
    proc_status: UploadProcStatusGql
    uploaded_at: Optional[datetime]
    verified_at: Optional[datetime]
    created_at: str
    updated_at: str

@strawberry.type
class UploadTaskFile:
    """上传任务文件类型"""
    id: str
    uid: str
    original_path: str
    storage_path: str
    filename: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    total_chunks: int
    uploaded_chunks: int
    current_chunk: int
    progress: float
    upload_speed: Optional[float]
    estimated_time_remaining: Optional[float]
    extracted_metadata: Optional[JSON]  # Fixed: Use JSON scalar instead of Any
    proc_status: UploadProcStatusGql
    upload_started_at: Optional[datetime]
    upload_completed_at: Optional[datetime]
    created_at: str
    updated_at: str

@strawberry.type
class UploadTask:
    """上传任务类型"""
    id: str
    uid: str
    tenant_id: str
    title: str
    desc: Optional[str]
    task_type: Optional[UploadTaskTypeGql]
    source_type: UploadSourceTypeGql
    source_paths: List[str]
    upload_strategy: UploadStrategyGql
    max_parallel_uploads: int
    chunk_size: int
    preserve_structure: bool
    base_upload_path: Optional[str]
    auto_extract_metadata: bool
    file_type_filters: List[FileTypeGql]
    max_file_size: Optional[int]
    discovered_files: int
    processing_files: int
    total_files: int
    completed_files: int
    failed_files: int
    total_size: int
    uploaded_size: int
    file_metadata: Optional[JSON]  # Fixed: Use JSON scalar instead of Any
    directory_structure: Optional[JSON]  # Fixed: Use JSON scalar instead of Any
    proc_status: UploadProcStatusGql
    discovery_started_at: Optional[datetime]
    discovery_completed_at: Optional[datetime]
    created_at: str
    updated_at: str
    created_by: Optional[str]

@strawberry.type
class UploadTaskList:
    """上传任务集合类型"""
    task: UploadTask
    files: List[UploadTaskFile]
    total_files: int
    total_size: int
    total_chunks: int
# input & response
#上传： 初始化
@strawberry.type
class UploadTaskFileData:
    """上传文件信息输入"""
    filename: str
    original_path: str
    storage_path: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    extracted_metadata: Optional[JSON] = None  # Fixed: Use JSON scalar instead of Any
    relative_path: Optional[str] = None

@strawberry.type
class UploadTaskInput(BaseInput):
    """上传任务初始化输入 - 包含任务和文件信息"""
    source_type: UploadSourceTypeGql
    title: str
    desc: Optional[str] = None
    upload_strategy: Optional[UploadStrategyGql] = UploadStrategyGql.PARALLEL
    max_parallel_uploads: Optional[int] = 5
    chunk_size: Optional[int] = 5 * 1024 * 1024  # 10MB
    preserve_structure: Optional[bool] = True
    base_upload_path: Optional[str] = None
    auto_extract_metadata: Optional[bool] = True
    file_type_filters: Optional[List[FileTypeGql]] = strawberry.field(default_factory=list)
    max_file_size: Optional[int] = None
    files: List[UploadTaskFileData]


@strawberry.type
class UploadTaskInitResponse(MutationResponse):
    """上传任务初始化响应"""
    data: Optional[UploadTaskList] = None
    task_id: Optional[str] = None


@strawberry.input
class UploadTaskFileChunkInput:
    """文件分块上传输入"""
    task_id: str
    file_id: str
    chunk_number: int
    chunk_data: Upload
    is_final_chunk: Optional[bool] = False
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None


@strawberry.input
class UploadTaskCompleteInput:
    """上传任务完成输入"""
    task_id: str
    force_complete: Optional[bool] = False


@strawberry.type
class UploadChunkResponse(MutationResponse):
    """上传分块响应"""
    file_id: Optional[str] = None
    next_chunk: Optional[int] = None
    progress: Optional[float] = None
    is_completed: Optional[bool] = None

@strawberry.type
class UploadTaskCompleteResponse(MutationResponse):
    """上传任务完成响应"""
    completed_files: int = 0
    failed_files: int = 0
    total_files: int = 0

@strawberry.type
class UploadProgressType:
    """上传进度类型"""
    task_id: str
    total_files: int
    completed_files: int
    failed_files: int
    total_size: int
    uploaded_size: int
    progress_percentage: float
    estimated_remaining_time: Optional[float]

@strawberry.type
class UploadStatsType:
    """上传统计类型"""
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_files_uploaded: int
    total_data_uploaded: int
    average_upload_speed: Optional[float]
