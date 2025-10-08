from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from foxmask.file.enums import FileTypeEnum, FileProcStatusEnum
from foxmask.core.enums import Status, Visibility


@dataclass
class FileCreateDTO:
    """文件创建DTO"""
    filename: str
    file_size: int
    storage_bucket: str
    storage_path: str
    extension: str
    title: str
    tenant_id: str
    content_type: str = "application/octet-stream"
    file_type: FileTypeEnum = FileTypeEnum.OTHER
    proc_status: FileProcStatusEnum = FileProcStatusEnum.PENDING
    download_count: int = 0
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_by: Optional[str] = None
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileUpdateDTO:
    """文件更新DTO"""
    filename: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    extension: Optional[str] = None
    file_type: Optional[FileTypeEnum] = None
    storage_bucket: Optional[str] = None
    storage_path: Optional[str] = None
    download_count: Optional[int] = None
    proc_status: Optional[FileProcStatusEnum] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    proc_meta: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FileResponseDTO:
    """文件响应DTO"""
    uid: str
    tenant_id: str
    filename: str
    file_size: int
    content_type: str
    extension: str
    file_type: FileTypeEnum
    storage_bucket: str
    storage_path: str
    download_count: int
    proc_status: FileProcStatusEnum
    title: str
    desc: Optional[str]
    category: Optional[str]
    tags: List[str]
    note: Optional[str]
    status: Status
    visibility: Visibility
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    created_by: Optional[str]
    allowed_users: List[str]
    allowed_roles: List[str]
    proc_meta: Dict[str, Any]
    error_info: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]


@dataclass
class FileListDTO:
    """文件列表DTO"""
    uid: str
    tenant_id: str
    filename: str
    file_size: int
    content_type: str
    extension: str
    file_type: FileTypeEnum
    download_count: int
    proc_status: FileProcStatusEnum
    title: str
    status: Status
    visibility: Visibility
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]


@dataclass
class FileDownloadDTO:
    """文件下载DTO"""
    uid: str
    filename: str
    file_size: int
    content_type: str
    storage_bucket: str
    storage_path: str
    download_count: int
    title: str
    tenant_id: str


@dataclass
class FileUploadResponseDTO:
    """文件上传响应DTO"""
    uid: str
    filename: str
    file_size: int
    content_type: str
    extension: str
    file_type: FileTypeEnum
    storage_bucket: str
    storage_path: str
    title: str
    tenant_id: str
    upload_url: Optional[str] = None
    expires_in: Optional[int] = None


@dataclass
class FileQueryDTO:
    """文件查询DTO"""
    tenant_id: str
    filename: Optional[str] = None
    title: Optional[str] = None
    file_type: Optional[FileTypeEnum] = None
    proc_status: Optional[FileProcStatusEnum] = None
    content_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    created_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


@dataclass
class FileSearchDTO:
    """文件搜索DTO"""
    tenant_id: str
    keyword: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    file_type: Optional[FileTypeEnum] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    created_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


# 添加缺失的 FileLogQueryDTO
@dataclass
class FileLogQueryDTO:
    """文件日志查询DTO"""
    tenant_id: str
    master_id: Optional[str] = None
    operation: Optional[str] = None
    operated_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


@dataclass
class FileStatisticsDTO:
    """文件统计DTO"""
    tenant_id: str
    total_files: int
    total_size: int
    file_type_distribution: Dict[FileTypeEnum, int]
    status_distribution: Dict[Status, int]
    proc_status_distribution: Dict[FileProcStatusEnum, int]
    visibility_distribution: Dict[Visibility, int]


@dataclass
class FileBulkUpdateDTO:
    """文件批量更新DTO"""
    uids: List[str]
    tenant_id: str
    update_data: FileUpdateDTO


@dataclass
class FileShareDTO:
    """文件分享DTO"""
    uid: str
    tenant_id: str
    allowed_users: List[str]
    allowed_roles: List[str]
    visibility: Visibility


@dataclass
class FileLogCreateDTO:
    """文件日志创建DTO"""
    master_id: str
    tenant_id: str
    operation: str
    operated_by: str
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    operation_time: datetime = field(default_factory=datetime.now)


@dataclass
class FileLogResponseDTO:
    """文件日志响应DTO"""
    uid: str
    tenant_id: str
    master_id: str
    operation: str
    operated_by: str
    operation_time: datetime
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: Status