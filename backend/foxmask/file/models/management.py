# 
# foxmask/file/models/management.py
from datetime import datetime, timezone
from typing import  Optional, Dict, Any

from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING

from foxmask.core.model import MasterBaseModel, SlaveBaseModel
from foxmask.file.enums import FileTypeEnum, FileProcStatusEnum


class File(MasterBaseModel):
    """文件模型 - 简化版，仅包含核心增删改查功能"""
    
    # 基础文件信息
    filename: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="原始文件名"
    )
    file_size: int = Field(
        ..., 
        ge=0, 
        le=100 * 1024 * 1024 * 1024,  # 100GB限制
        description="文件大小（字节）"
    )
    content_type: str = Field(
        default="application/octet-stream", 
        description="内容类型"
    )
    extension: str = Field(
        ..., 
        max_length=20, 
        description="文件扩展名"
    )
    file_type: FileTypeEnum = Field(
        default=FileTypeEnum.OTHER, 
        description="文件类型"
    )
    
    # 存储信息
    storage_bucket: str = Field(
        ..., 
        description="存储桶"
    )
    storage_path: str = Field(
        ..., 
        description="存储路径"
    )
    
    # 统计信息
    download_count: int = Field(
        default=0, 
        ge=0, 
        description="下载次数"
    )
    
    # 处理状态
    proc_status: FileProcStatusEnum = Field(
        default=FileProcStatusEnum.PENDING, 
        description="处理状态"
    )
    
    class Settings:
        """MongoDB 集合配置"""
        name = "files"
        indexes = [
            IndexModel([("uid", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("uid", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
        ]


class FileLog(SlaveBaseModel):
    """文件操作日志模型 - 简化版"""
    
    operation: str = Field(
        ..., 
        description="操作类型"
    )
    operated_by: str = Field(
        ..., 
        description="操作用户ID"
    )
    operation_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="操作时间"
    )
    
    # 操作详情
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="操作详情"
    )
    ip_address: Optional[str] = Field(
        None, 
        description="IP地址"
    )
    
    class Settings:
        """MongoDB 集合配置"""
        name = "file_logs"
        indexes = [
            IndexModel([("uid", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("master_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]