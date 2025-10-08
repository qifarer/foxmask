# -*- coding: utf-8 -*-
# foxmask/file/models/upload.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import Field
from beanie import Document

from foxmask.core.model import MasterBaseModel, SlaveBaseModel
from foxmask.file.enums import (
    FileTypeEnum, 
    UploadProcStatusEnum, 
    UploadSourceTypeEnum, 
    UploadStrategyEnum
)


class UploadTask(MasterBaseModel):
    """上传任务模型"""
    
    # 基础信息
    proc_status: UploadProcStatusEnum = Field(
        default=UploadProcStatusEnum.PENDING, 
        description="任务处理状态"
    )
    
    # 上传源信息
    source_type: UploadSourceTypeEnum = Field(
        ..., 
        description="上传源类型"
    )
    source_paths: List[str] = Field(
        ..., 
        description="源路径列表"
    )
    
    # 上传配置
    upload_strategy: UploadStrategyEnum = Field(
        default=UploadStrategyEnum.SEQUENTIAL, 
        description="上传策略"
    )
    max_parallel_uploads: int = Field(
        default=5, 
        ge=1, 
        le=50, 
        description="最大并行上传数"
    )
    chunk_size: int = Field(
        default=10 * 1024 * 1024, 
        ge=1 * 1024 * 1024, 
        description="分块大小（字节）"
    )
    
    # 目录处理
    preserve_structure: bool = Field(
        default=True, 
        description="是否保持目录结构"
    )
    base_upload_path: Optional[str] = Field(
        None, 
        description="基础上传路径"
    )
    
    # 自动元数据提取
    auto_extract_metadata: bool = Field(
        default=True, 
        description="是否自动提取元数据"
    )
    file_type_filters: List[FileTypeEnum] = Field(
        default_factory=list, 
        description="文件类型过滤器"
    )
    max_file_size: Optional[int] = Field(
        None, 
        ge=0, 
        description="最大文件大小限制（字节）"
    )
    
    # 进度统计
    discovered_files: int = Field(
        default=0, 
        ge=0, 
        description="已发现文件数"
    )
    processing_files: int = Field(
        default=0, 
        ge=0, 
        description="处理中文件数"
    )
    total_files: int = Field(
        default=0, 
        ge=0, 
        description="总文件数"
    )
    completed_files: int = Field(
        default=0, 
        ge=0, 
        description="已完成文件数"
    )
    failed_files: int = Field(
        default=0, 
        ge=0, 
        description="失败文件数"
    )
    total_size: int = Field(
        default=0, 
        ge=0, 
        description="总文件大小（字节）"
    )
    uploaded_size: int = Field(
        default=0, 
        ge=0, 
        description="已上传大小（字节）"
    )
    
    # 时间戳
    discovery_started_at: Optional[datetime] = Field(
        None, 
        description="文件发现开始时间"
    )
    discovery_completed_at: Optional[datetime] = Field(
        None, 
        description="文件发现完成时间"
    )
    
    class Settings:
        """MongoDB 集合配置"""
        name = "upload_tasks"
        indexes = [
            [("uid", 1)],
            [("tenant_id", 1), ("source_type", 1)],
            [("created_at", -1)],
            [("proc_status", 1)],
        ]


class UploadTaskFile(SlaveBaseModel):
    """上传任务文件模型"""
    
    proc_status: UploadProcStatusEnum = Field(
        default=UploadProcStatusEnum.PENDING, 
        description="文件处理状态"
    )
    
    # 文件标识
    original_path: str = Field(
        ..., 
        description="原始文件路径"
    )
    storage_path: str = Field(
        ..., 
        description="存储路径"
    )
    filename: str = Field(
        ..., 
        description="文件名"
    )
    
    # 文件信息
    file_size: int = Field(
        ..., 
        ge=0, 
        description="文件大小（字节）"
    )
    file_type: FileTypeEnum = Field(
        default=FileTypeEnum.OTHER, 
        description="文件类型"
    )
    content_type: str = Field(
        default="application/octet-stream", 
        description="内容类型"
    )
    extension: str = Field(
        ..., 
        description="文件扩展名"
    )
    
    # 存储信息
    minio_bucket: Optional[str] = Field(
        None, 
        description="MinIO 存储桶"
    )
    minio_object_name: Optional[str] = Field(
        None, 
        description="MinIO 对象名称"
    )
    minio_etag: Optional[str] = Field(
        None, 
        description="MinIO ETag"
    )
    
    # 校验信息
    checksum_md5: Optional[str] = Field(
        None, 
        description="MD5 校验和"
    )
    checksum_sha256: Optional[str] = Field(
        None, 
        description="SHA256 校验和"
    )
    
    # 上传控制
    total_chunks: int = Field(
        ..., 
        ge=1, 
        description="总分块数"
    )
    uploaded_chunks: int = Field(
        default=0, 
        ge=0, 
        description="已上传分块数"
    )
    current_chunk: int = Field(
        default=0, 
        ge=0, 
        description="当前分块索引"
    )
    
    # 进度信息
    progress: float = Field(
        default=0.0, 
        ge=0.0, 
        le=100.0, 
        description="上传进度百分比"
    )
    upload_speed: Optional[float] = Field(
        None, 
        description="上传速度（字节/秒）"
    )
    estimated_time_remaining: Optional[float] = Field(
        None, 
        description="预计剩余时间（秒）"
    )
    
    # 元数据
    extracted_metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="自动提取的元数据"
    )
    
    # 时间戳
    upload_started_at: Optional[datetime] = Field(
        None, 
        description="上传开始时间"
    )
    upload_completed_at: Optional[datetime] = Field(
        None, 
        description="上传完成时间"
    )
    
    class Settings:
        """MongoDB 集合配置"""
        name = "upload_task_files"
        indexes = [
            [("uid", 1)],
            [("tenant_id", 1), ("master_id", 1)],
            [("proc_status", 1)],
            [("original_path", 1)],
        ]


class UploadTaskFileChunk(SlaveBaseModel):
    """文件分块模型"""
    
    proc_status: UploadProcStatusEnum = Field(
        default=UploadProcStatusEnum.PENDING, 
        description="分块处理状态"
    )
    
    # 分块标识
    file_id: str = Field(
        ..., 
        description="文件ID"
    )
    chunk_number: int = Field(
        ..., 
        ge=1, 
        description="分块编号"
    )
    chunk_size: int = Field(
        ..., 
        ge=0, 
        description="分块大小（字节）"
    )
    
    # 字节范围
    start_byte: int = Field(
        ..., 
        ge=0, 
        description="起始字节"
    )
    end_byte: int = Field(
        ..., 
        ge=0, 
        description="结束字节"
    )
    is_final_chunk: bool = Field(
        default=False, 
        description="是否为最后分块"
    )
    
    # 存储信息
    minio_bucket: str = Field(
        ..., 
        description="MinIO 存储桶"
    )
    minio_object_name: str = Field(
        ..., 
        description="MinIO 对象名称"
    )
    minio_etag: Optional[str] = Field(
        None, 
        description="MinIO ETag"
    )
    
    # 校验信息
    checksum_md5: Optional[str] = Field(
        None, 
        description="MD5 校验和"
    )
    checksum_sha256: Optional[str] = Field(
        None, 
        description="SHA256 校验和"
    )
    
    # 重试控制
    retry_count: int = Field(
        default=0, 
        ge=0, 
        description="重试次数"
    )
    max_retries: int = Field(
        default=3, 
        ge=0, 
        description="最大重试次数"
    )
    
    class Settings:
        """MongoDB 集合配置"""
        name = "upload_task_file_chunks"
        indexes = [
            [("uid", 1)],
            [("tenant_id", 1), ("file_id", 1), ("uid", 1)],
            [("proc_status", 1)],
        ]