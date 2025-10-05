# -*- coding: utf-8 -*-
# foxmask/file/schema/management.py
import strawberry
from typing import Optional, List, Annotated
from datetime import datetime
from strawberry.scalars import JSON

from .enums import VisibilityGql,StatusGql,FileTypeGql,UploadProcStatusGql

@strawberry.type
class FileType:
    """文件GraphQL类型"""
    uid: str
    tenant_id: str
    title: str
    desc: Optional[str]
    category: Optional[str]
    tags: List[str]
    note: Optional[str]
    status: StatusGql
    visibility: VisibilityGql
    
    # 文件特定字段
    original_filename: str
    file_size: int
    content_type: str
    extension: str
    file_type: FileTypeGql
    storage_bucket: str
    storage_key: str
    storage_path: str
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    download_count: int
    file_status: UploadProcStatusGql
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    created_by: Optional[str]
    
    # 权限控制
    allowed_users: List[str]
    allowed_roles: List[str]
    
    # 元数据
    metadata: JSON


@strawberry.input
class FileCreateInput:
    """文件创建输入类型"""
    original_filename: str
    file_size: int
    content_type: str = "application/octet-stream"
    extension: str
    file_type: FileTypeGql = FileTypeGql.OTHER
    storage_bucket: str
    storage_key: str
    storage_path: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    note: Optional[str] = None
    visibility: VisibilityGql = VisibilityGql.PUBLIC
    allowed_users: Optional[List[str]] = strawberry.field(default_factory=list)
    allowed_roles: Optional[List[str]] = strawberry.field(default_factory=list)
    metadata: Optional[JSON] = None


@strawberry.input
class FileUpdateInput:
    """文件更新输入类型"""
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_type: Optional[FileTypeGql] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    file_status: Optional[UploadProcStatusGql] = None
    visibility: Optional[VisibilityGql] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None


@strawberry.input
class FileQueryInput:
    """文件查询输入类型"""
    title: Optional[str] = None
    original_filename: Optional[str] = None
    file_type: Optional[FileTypeGql] = None
    file_status: Optional[UploadProcStatusGql] = None
    content_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None
    visibility: Optional[VisibilityGql] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


@strawberry.type
class FileListType:
    """文件列表类型"""
    items: List[FileType]
    total: int
    page: int
    size: int
    pages: int


# ==================== FileLog GraphQL类型 ====================

@strawberry.type
class FileLogType:
    """文件日志GraphQL类型"""
    uid: str
    tenant_id: str
    master_id: str
    operation: str
    operated_by: str
    operation_time: datetime
    details: Optional[JSON]
    ip_address: Optional[str]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class FileLogCreateInput:
    """文件日志创建输入类型"""
    operation: str
    operated_by: str
    details: Optional[JSON] = None
    ip_address: Optional[str] = None
    note: Optional[str] = None


@strawberry.input
class FileLogQueryInput:
    """文件日志查询输入类型"""
    operation: Optional[str] = None
    operated_by: Optional[str] = None
    master_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    size: int = 50
    sort_by: str = "operation_time"
    sort_order: str = "desc"


@strawberry.type
class FileLogListType:
    """文件日志列表类型"""
    items: List[FileLogType]
    total: int
    page: int
    size: int
    pages: int


# ==================== 统计类型 ====================

@strawberry.type
class FileStatsType:
    """文件统计类型"""
    total_files: int
    total_size: int
    pending_files: int
    processed_files: int
    failed_files: int
    by_file_type: JSON
    by_content_type: JSON
    daily_uploads: JSON


@strawberry.type
class FileOperationStatsType:
    """文件操作统计类型"""
    total_operations: int
    by_operation_type: JSON
    by_user: JSON
    daily_operations: JSON


# ==================== 响应类型 ====================

@strawberry.type
class FileResponse:
    """文件响应类型"""
    success: bool
    message: str
    data: Optional[FileType] = None
    code: int = 200


@strawberry.type
class FileListResponse:
    """文件列表响应类型"""
    success: bool
    message: str
    data: Optional[FileListType] = None
    code: int = 200


@strawberry.type
class FileLogResponse:
    """文件日志响应类型"""
    success: bool
    message: str
    data: Optional[FileLogType] = None
    code: int = 200


@strawberry.type
class FileLogListResponse:
    """文件日志列表响应类型"""
    success: bool
    message: str
    data: Optional[FileLogListType] = None
    code: int = 200


@strawberry.type
class FileStatsResponse:
    """文件统计响应类型"""
    success: bool
    message: str
    data: Optional[FileStatsType] = None
    code: int = 200


@strawberry.type
class FileOperationStatsResponse:
    """文件操作统计响应类型"""
    success: bool
    message: str
    data: Optional[FileOperationStatsType] = None
    code: int = 200


# ==================== 文件上传相关类型 ====================

@strawberry.input
class FileUploadInput:
    """文件上传输入类型"""
    filename: str
    file_size: int
    content_type: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: VisibilityGql = VisibilityGql.PUBLIC


@strawberry.type
class FileUploadResponse:
    """文件上传响应类型"""
    success: bool
    message: str
    file_id: Optional[str] = None
    upload_url: Optional[str] = None
    code: int = 200


@strawberry.type
class FileDownloadResponse:
    """文件下载响应类型"""
    success: bool
    message: str
    download_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    code: int = 200