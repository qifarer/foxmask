# -*- coding: utf-8 -*-
# foxmask/file/dto/management.py
from typing import Optional, List, Dict, Any
from pydantic import Field, ConfigDict
from datetime import datetime

from foxmask.core.model import Visibility, Status
from foxmask.file.enums import FileTypeEnum, UploadProcStatusEnum


# ==================== File DTOs ====================

class FileCreateDTO:
    """文件创建DTO"""
    
    original_filename: str = Field(..., min_length=1, max_length=500, description="原始文件名")
    file_size: int = Field(..., ge=0, le=100*1024*1024*1024, description="文件大小（字节）")
    content_type: str = Field(default="application/octet-stream", description="内容类型")
    extension: str = Field(..., max_length=20, description="文件扩展名")
    file_type: FileTypeEnum = Field(default=FileTypeEnum.OTHER, description="文件类型")
    storage_bucket: str = Field(..., description="存储桶")
    storage_key: str = Field(..., description="存储键")
    storage_path: str = Field(..., description="存储路径")
    checksum_md5: Optional[str] = Field(None, pattern=r'^[a-fA-F0-9]{32}$', description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, pattern=r'^[a-fA-F0-9]{64}$', description="SHA256校验和")
    title: Optional[str] = Field(None, min_length=1, max_length=300, description="标题")
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="可见性")
    allowed_users: List[str] = Field(default_factory=list, description="允许访问的用户")
    allowed_roles: List[str] = Field(default_factory=list, description="允许访问的角色")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileUpdateDTO:
    """文件更新DTO"""
    
    original_filename: Optional[str] = Field(None, min_length=1, max_length=500, description="原始文件名")
    content_type: Optional[str] = Field(None, description="内容类型")
    file_type: Optional[FileTypeEnum] = Field(None, description="文件类型")
    title: Optional[str] = Field(None, min_length=1, max_length=300, description="标题")
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    note: Optional[str] = Field(None, description="备注")
    file_status: Optional[UploadProcStatusEnum] = Field(None, description="文件状态")
    visibility: Optional[Visibility] = Field(None, description="可见性")
    allowed_users: Optional[List[str]] = Field(None, description="允许访问的用户")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定义元数据")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileResponseDTO:
    """文件响应DTO"""
    
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    title: str = Field(..., description="标题")
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    status: Status = Field(..., description="记录状态")
    visibility: Visibility = Field(..., description="知识可用性级别")
    
    # 文件特定字段
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    content_type: str = Field(..., description="内容类型")
    extension: str = Field(..., description="文件扩展名")
    file_type: FileTypeEnum = Field(..., description="文件类型")
    storage_bucket: str = Field(..., description="存储桶")
    storage_key: str = Field(..., description="存储键")
    storage_path: str = Field(..., description="存储路径")
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")
    download_count: int = Field(..., description="下载次数")
    file_status: UploadProcStatusEnum = Field(..., description="处理状态")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    archived_at: Optional[datetime] = Field(None, description="归档时间")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    
    # 权限控制
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileQueryDTO:
    """文件查询DTO"""
    
    title: Optional[str] = Field(None, description="标题关键词")
    original_filename: Optional[str] = Field(None, description="原始文件名关键词")
    file_type: Optional[FileTypeEnum] = Field(None, description="文件类型")
    file_status: Optional[UploadProcStatusEnum] = Field(None, description="文件状态")
    content_type: Optional[str] = Field(None, description="内容类型")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_by: Optional[str] = Field(None, description="创建者")
    visibility: Optional[Visibility] = Field(None, description="可见性")
    
    # 文件大小范围
    min_size: Optional[int] = Field(None, ge=0, description="最小文件大小")
    max_size: Optional[int] = Field(None, ge=0, description="最大文件大小")
    
    # 时间范围
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    
    # 分页排序
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileListDTO:
    """文件列表DTO"""
    
    items: List[FileResponseDTO] = Field(..., description="文件列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# ==================== FileLog DTOs ====================

class FileLogCreateDTO:
    """文件日志创建DTO"""
    
    operation: str = Field(..., description="操作类型")
    operated_by: str = Field(..., description="操作用户ID")
    details: Optional[Dict[str, Any]] = Field(None, description="操作详情")
    ip_address: Optional[str] = Field(None, description="IP地址")
    note: Optional[str] = Field(None, description="备注")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileLogResponseDTO:
    """文件日志响应DTO"""
    
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    master_id: str = Field(..., description="主文档ID")
    
    # 日志特定字段
    operation: str = Field(..., description="操作类型")
    operated_by: str = Field(..., description="操作用户ID")
    operation_time: datetime = Field(..., description="操作时间")
    details: Optional[Dict[str, Any]] = Field(None, description="操作详情")
    ip_address: Optional[str] = Field(None, description="IP地址")
    note: Optional[str] = Field(None, description="备注")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileLogQueryDTO:
    """文件日志查询DTO"""
    
    operation: Optional[str] = Field(None, description="操作类型")
    operated_by: Optional[str] = Field(None, description="操作用户ID")
    master_id: Optional[str] = Field(None, description="主文件ID")
    
    # 时间范围
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    
    # 分页排序
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=50, ge=1, le=200, description="每页大小")
    sort_by: str = Field(default="operation_time", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileLogListDTO:
    """文件日志列表DTO"""
    
    items: List[FileLogResponseDTO] = Field(..., description="日志列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# ==================== 统计 DTO ====================

class FileStatsDTO:
    """文件统计DTO"""
    
    total_files: int = Field(..., description="总文件数")
    total_size: int = Field(..., description="总文件大小（字节）")
    pending_files: int = Field(..., description="待处理文件数")
    processed_files: int = Field(..., description="已处理文件数")
    failed_files: int = Field(..., description="失败文件数")
    by_file_type: Dict[str, int] = Field(..., description="按文件类型统计")
    by_content_type: Dict[str, int] = Field(..., description="按内容类型统计")
    daily_uploads: Dict[str, int] = Field(..., description="每日上传统计")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class FileOperationStatsDTO:
    """文件操作统计DTO"""
    
    total_operations: int = Field(..., description="总操作数")
    by_operation_type: Dict[str, int] = Field(..., description="按操作类型统计")
    by_user: Dict[str, int] = Field(..., description="按用户统计")
    daily_operations: Dict[str, int] = Field(..., description="每日操作统计")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )