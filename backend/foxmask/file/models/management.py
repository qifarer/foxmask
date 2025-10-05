#foxmask/file/models/management.py
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from beanie import Link
from pydantic import Field, field_validator, ConfigDict
from pymongo import IndexModel, ASCENDING, DESCENDING

from foxmask.core.model import (
    MasterBaseModel,SlaveBaseModel
)
from foxmask.file.enums import FileTypeEnum , UploadProcStatusEnum


class File(MasterBaseModel):
    """文件模型 - 简化版，仅包含核心增删改查功能"""
    
    # 基础文件信息
    original_filename: str = Field(..., min_length=1, max_length=500, description="原始文件名")
    file_size: int = Field(..., ge=0, le=100*1024*1024*1024, description="文件大小（字节）")  # 100GB限制
    content_type: str = Field(default="application/octet-stream", description="内容类型")
    extension: str = Field(..., max_length=20, description="文件扩展名")
    file_type: FileTypeEnum = Field(default=FileTypeEnum.OTHER, description="文件类型")
    
    # 存储信息
    storage_bucket: str = Field(..., description="存储桶")
    storage_key: str = Field(..., description="存储键")
    storage_path: str = Field(..., description="存储路径")
    
    # 校验信息
    checksum_md5: Optional[str] = Field(None, pattern=r'^[a-fA-F0-9]{32}$', description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, pattern=r'^[a-fA-F0-9]{64}$', description="SHA256校验和")
    
    # 统计信息
    download_count: int = Field(default=0, ge=0, description="下载次数")
    # 处理状态
    file_status: UploadProcStatusEnum = Field(default=UploadProcStatusEnum.PENDING, description="处理状态")
    
    class Settings:
        name = "files"
        indexes = [
            IndexModel([("uid", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("uid", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
        ]
    

class FileLog(SlaveBaseModel):
    """文件操作日志模型 - 简化版"""
    
    operation: str = Field(..., description="操作类型")
    operated_by: str = Field(..., description="操作用户ID")
    operation_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="操作时间"
    )
    
    # 操作详情
    details: Optional[Dict[str, Any]] = Field(None, description="操作详情")
    ip_address: Optional[str] = Field(None, description="IP地址")
    
    
    class Settings:
        name = "file_logs"
        indexes = [
            IndexModel([("uid", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("master_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]
    
    
