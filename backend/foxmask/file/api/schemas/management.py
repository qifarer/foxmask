# -*- coding: utf-8 -*-
# foxmask/file/api/schemas/file.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from .base import BaseResponse, PaginationParams, ListResponse


class FileTypeEnum(str, Enum):
    """文件类型枚举"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"

class FileStatus(str, Enum):
    """文件状态枚举"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    PROCESSING = "processing"
    ERROR = "error"

class Visibility(str, Enum):
    """可见性枚举"""
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"


class FileCreateRequest(BaseModel):
    """创建文件记录请求"""
    original_filename: str = Field(..., min_length=1, max_length=500, description="原始文件名")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    content_type: str = Field(..., description="内容类型")
    extension: str = Field(..., description="文件扩展名")
    file_type: FileTypeEnum = Field(..., description="文件类型")
    storage_bucket: str = Field(..., description="存储桶")
    storage_key: str = Field(..., description="存储键")
    storage_path: str = Field(..., description="存储路径")
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")
    title: Optional[str] = Field(None, min_length=1, max_length=300, description="文件标题")
    desc: Optional[str] = Field(None, description="文件描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="可见性")
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")


class FileUpdateRequest(BaseModel):
    """更新文件信息请求"""
    original_filename: Optional[str] = Field(None, min_length=1, max_length=500, description="原始文件名")
    content_type: Optional[str] = Field(None, description="内容类型")
    file_type: Optional[FileTypeEnum] = Field(None, description="文件类型")
    title: Optional[str] = Field(None, min_length=1, max_length=300, description="文件标题")
    desc: Optional[str] = Field(None, description="文件描述")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    note: Optional[str] = Field(None, description="备注")
    file_status: Optional[FileStatus] = Field(None, description="文件状态")
    visibility: Optional[Visibility] = Field(None, description="可见性")
    allowed_users: Optional[List[str]] = Field(None, description="有访问权限的用户ID列表")
    allowed_roles: Optional[List[str]] = Field(None, description="有访问权限的角色列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定义元数据")



class FileResponse(BaseModel):
    """文件响应"""
    id: str = Field(..., description="文件ID")
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户ID")
    
    # 文件基本信息
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小")
    content_type: str = Field(..., description="内容类型")
    extension: str = Field(..., description="文件扩展名")
    file_type: FileTypeEnum = Field(..., description="文件类型")
    
    # 存储信息
    storage_bucket: str = Field(..., description="存储桶")
    storage_key: str = Field(..., description="存储键")
    storage_path: str = Field(..., description="存储路径")
    
    # 校验信息
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")
    
    # 元数据信息
    title: str = Field(..., description="文件标题")
    desc: Optional[str] = Field(None, description="文件描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    
    # 状态和权限
    file_status: FileStatus = Field(..., description="文件状态")
    visibility: Visibility = Field(..., description="可见性")
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    
    # 统计信息
    download_count: int = Field(default=0, description="下载次数")
    view_count: int = Field(default=0, description="查看次数")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    archived_at: Optional[datetime] = Field(None, description="归档时间")
    created_by: Optional[str] = Field(None, description="创建者")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileQueryParams(PaginationParams):
    """文件查询参数"""
    title: Optional[str] = Field(None, description="标题关键词")
    original_filename: Optional[str] = Field(None, description="原始文件名关键词")
    file_type: Optional[FileTypeEnum] = Field(None, description="文件类型")
    file_status: Optional[FileStatus] = Field(None, description="文件状态")
    content_type: Optional[str] = Field(None, description="内容类型")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_by: Optional[str] = Field(None, description="创建者")
    visibility: Optional[Visibility] = Field(None, description="可见性")
    min_size: Optional[int] = Field(None, ge=0, description="最小文件大小")
    max_size: Optional[int] = Field(None, ge=0, description="最大文件大小")
    start_date: Optional[str] = Field(None, description="开始时间")
    end_date: Optional[str] = Field(None, description="结束时间")

   

class FileListResponse(ListResponse[FileResponse]):
    """文件列表响应"""
    pass


class FileStatsResponse(BaseResponse):
    """文件统计响应"""
    total_files: int = Field(0, description="总文件数")
    active_files: int = Field(0, description="活跃文件数")
    archived_files: int = Field(0, description="已归档文件数")
    total_storage_size: int = Field(0, description="总存储大小")
    average_file_size: float = Field(0.0, description="平均文件大小")
    file_type_distribution: Dict[str, int] = Field(default_factory=dict, description="文件类型分布")
    daily_uploads: int = Field(0, description="今日上传数")
    weekly_uploads: int = Field(0, description="本周上传数")
    monthly_uploads: int = Field(0, description="本月上传数")


class FileUploadRequest(BaseModel):
    """文件上传请求"""
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., ge=0, description="文件大小")
    content_type: str = Field(..., description="内容类型")
    file_type: FileTypeEnum = Field(default=FileTypeEnum.OTHER, description="文件类型")
    title: Optional[str] = Field(None, description="文件标题")
    desc: Optional[str] = Field(None, description="文件描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="可见性")

    

class FileUploadResponse(BaseResponse):
    """文件上传响应"""
    file_id: Optional[str] = Field(None, description="文件ID")
    upload_url: Optional[str] = Field(None, description="上传URL")
    upload_id: Optional[str] = Field(None, description="上传ID")
    expires_at: Optional[datetime] = Field(None, description="URL过期时间")


class FileDownloadResponse(BaseResponse):
    """文件下载响应"""
    download_url: Optional[str] = Field(None, description="下载URL")
    filename: Optional[str] = Field(None, description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小")
    content_type: Optional[str] = Field(None, description="内容类型")
    expires_at: Optional[datetime] = Field(None, description="URL过期时间")


class ErrorResponse(BaseResponse):
    """错误响应"""
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    trace_id: Optional[str] = Field(None, description="请求追踪ID")