# -*- coding: utf-8 -*-
# foxmask/file/graphql/schemas/management.py
from typing import List, Optional
import strawberry
from strawberry.scalars import JSON
from datetime import datetime
from enum import Enum
from foxmask.core.schema import StatusEnum,VisibilityEnum

# 直接在GraphQL schema中定义枚举，不使用原始枚举的引用
@strawberry.enum
class FileTypeEnum(Enum):
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    OTHER = "OTHER"


@strawberry.enum
class FileProcStatusEnum(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@strawberry.input
class FileCreateInput:
    """文件创建输入"""
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
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    note: Optional[str] = None
    status: StatusEnum = StatusEnum.DRAFT
    visibility: VisibilityEnum = VisibilityEnum.PUBLIC
    created_by: Optional[str] = None
    allowed_users: Optional[List[str]] = strawberry.field(default_factory=list)
    allowed_roles: Optional[List[str]] = strawberry.field(default_factory=list)
    metadata: Optional[JSON] = None


@strawberry.input
class FileUpdateInput:
    """文件更新输入"""
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
    status: Optional[StatusEnum] = None
    visibility: Optional[VisibilityEnum] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    proc_meta: Optional[JSON] = None
    error_info: Optional[JSON] = None
    metadata: Optional[JSON] = None


@strawberry.type
class FileType:
    """文件类型"""
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
    status: StatusEnum
    visibility: VisibilityEnum
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    created_by: Optional[str]
    allowed_users: List[str]
    allowed_roles: List[str]
    proc_meta: JSON
    error_info: Optional[JSON]
    metadata: JSON


@strawberry.type
class FileListType:
    """文件列表类型"""
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
    status: StatusEnum
    visibility: VisibilityEnum
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]


@strawberry.type
class FileDownloadType:
    """文件下载类型"""
    uid: str
    filename: str
    file_size: int
    content_type: str
    storage_bucket: str
    storage_path: str
    download_count: int
    title: str
    tenant_id: str


@strawberry.type
class FileUploadResponseType:
    """文件上传响应类型"""
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


@strawberry.input
class FileQueryInput:
    """文件查询输入"""
    tenant_id: str
    filename: Optional[str] = None
    title: Optional[str] = None
    file_type: Optional[FileTypeEnum] = None
    proc_status: Optional[FileProcStatusEnum] = None
    content_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[StatusEnum] = None
    visibility: Optional[VisibilityEnum] = None
    created_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


@strawberry.type
class FileStatisticsType:
    """文件统计类型"""
    tenant_id: str
    total_files: int
    total_size: int
    file_type_distribution: JSON
    status_distribution: JSON
    proc_status_distribution: JSON
    visibility_distribution: JSON


@strawberry.input
class FileBulkUpdateInput:
    """文件批量更新输入"""
    uids: List[str]
    tenant_id: str
    update_data: FileUpdateInput


@strawberry.input
class FileShareInput:
    """文件分享输入"""
    uid: str
    tenant_id: str
    allowed_users: List[str]
    allowed_roles: List[str]
    visibility: VisibilityEnum


@strawberry.input
class FileLogCreateInput:
    """文件日志创建输入"""
    master_id: str
    tenant_id: str
    operation: str
    operated_by: str
    details: Optional[JSON] = None
    ip_address: Optional[str] = None
    operation_time: Optional[datetime] = None


@strawberry.type
class FileLogType:
    """文件日志类型"""
    uid: str
    tenant_id: str
    master_id: str
    operation: str
    operated_by: str
    operation_time: datetime
    details: Optional[JSON]
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: StatusEnum


@strawberry.input
class FileSearchInput:
    """文件搜索输入"""
    tenant_id: str
    keyword: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    file_type: Optional[FileTypeEnum] = None
    status: Optional[StatusEnum] = None
    visibility: Optional[VisibilityEnum] = None
    created_by: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


@strawberry.type
class FileListResult:
    """文件列表结果"""
    items: List[FileListType]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@strawberry.type
class FileSearchResult:
    """文件搜索结果"""
    items: List[FileListType]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@strawberry.type
class FileOperationResult:
    """文件操作结果"""
    success: bool
    message: str
    uid: Optional[str] = None


@strawberry.type
class FileBulkOperationResult:
    """文件批量操作结果"""
    success: bool
    message: str
    processed_count: int
    failed_count: int
    failed_items: List[str]

