# -*- coding: utf-8 -*-
# backend/foxmask/file/models.py   
# Copyright (C) 2024 FoxMask Inc.
# author: Roky

# 标准库导入
from datetime import datetime
from enum import Enum
import uuid
from typing import Optional, List, Dict, Any

# 第三方库导入
from beanie import Document
from pydantic import Field, ConfigDict, field_validator, model_validator
from pymongo import IndexModel, ASCENDING, DESCENDING

# 本地模块导入
from foxmask.utils.helpers import get_current_time
from foxmask.core.logger import logger


class FileStatus(str, Enum):
    """
    文件状态枚举
    定义文件在整个生命周期中的各种状态
    """
    DRAFT = "draft"          # 草稿状态，文件信息已创建但未开始上传
    UPLOADING = "uploading"  # 分片上传中
    UPLOADED = "uploaded"    # 所有分片上传完成
    VERIFYING = "verifying"  # 分片校验中
    VERIFIED = "verified"    # 所有分片校验完成
    PROCESSING = "processing"  # 文件处理中（如格式转换、索引等）
    COMPLETED = "completed"  # 文件处理完成，可供使用
    FAILED = "failed"        # 文件处理失败
    PARTIAL = "partial"      # 部分分片上传完成
    CANCELED = "canceled"    # 上传已取消


class ChunkStatus(str, Enum):
    """
    分片状态枚举
    定义单个文件分片的上传状态
    """
    PENDING = "pending"      # 分片等待上传
    UPLOADING = "uploading"  # 分片上传中
    UPLOADED = "uploaded"    # 分片上传完成
    VERIFIED = "verified"    # 分片校验完成
    FAILED = "failed"        # 分片上传失败


class FileVisibility(str, Enum):
    """
    文件可见性枚举
    定义文件的访问权限级别
    """
    PRIVATE = "private"      # 仅上传者可见
    TENANT = "tenant"        # 租户内所有用户可见
    PUBLIC = "public"        # 公开访问


class FileType(str, Enum):
    """
    文件类型枚举
    按用途对文件进行分类
    """
    PDF = "pdf"
    DOCUMENT = "document"      # 文档文件
    SPREADSHEET = "spreadsheet"  # 电子表格
    PRESENTATION = "presentation"  # 演示文稿
    TEXT = "text"              # 文本文件
    CODE = "code"              # 代码文件
    IMAGE = "image"            # 图片文件
    VECTOR = "vector"          # 矢量图形
    AUDIO = "audio"            # 音频文件
    VIDEO = "video"            # 视频文件
    JSON = "json"              # JSON文件
    XML = "xml"                # XML文件
    CSV = "csv"                # CSV文件
    ARCHIVE = "archive"        # 压缩文件
    BINARY = "binary"          # 二进制文件
    UNKNOWN = "unknown"        # 未知类型


# 文件类型扩展名映射
FILE_TYPE_EXTENSIONS = {
    FileType.PDF: ['.pdf'],
    FileType.DOCUMENT: ['.doc', '.docx', '.odt', '.rtf', '.docm'],
    FileType.SPREADSHEET: ['.xls', '.xlsx', '.ods', '.csv', '.xlsm'],
    FileType.PRESENTATION: ['.ppt', '.pptx', '.odp', '.pptm'],
    FileType.TEXT: ['.txt', '.md', '.markdown', '.log'],
    FileType.CODE: ['.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css', '.php', '.rb', '.go', '.ts'],
    FileType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'],
    FileType.VECTOR: ['.svg', '.ai', '.eps'],
    FileType.AUDIO: ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma'],
    FileType.VIDEO: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
    FileType.JSON: ['.json'],
    FileType.XML: ['.xml', '.rss', '.atom'],
    FileType.CSV: ['.csv'],
    FileType.ARCHIVE: ['.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.tar.gz'],
}

# 扩展名到文件类型的反向映射
EXTENSION_FILE_TYPES = {
    ext: file_type
    for file_type, extensions in FILE_TYPE_EXTENSIONS.items()
    for ext in extensions
}


class FileChunk(Document):
    """
    文件分片模型
    管理大文件分片上传的各个分片信息
    """
    
    # 分片基本信息
    file_id: str = Field(..., description="父文件ID")
    upload_id: str = Field(..., description="MinIO上传会话ID")
    chunk_number: int = Field(..., ge=1, description="分片编号（从1开始）")
    chunk_size: int = Field(..., ge=0, description="分片大小（字节）")
    start_byte: int = Field(..., ge=0, description="分片在文件中的起始字节位置")
    end_byte: int = Field(..., ge=0, description="分片在文件中的结束字节位置")
    
    # MinIO存储信息
    minio_object_name: str = Field(..., description="MinIO对象名称")
    minio_bucket: str = Field(..., description="MinIO存储桶名称")
    minio_etag: Optional[str] = Field(None, description="MinIO ETag标识")
    
    # 校验和信息
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")
    
    # 状态信息
    status: ChunkStatus = Field(ChunkStatus.PENDING, description="分片状态")
    retry_count: int = Field(0, description="重试次数")
    
    # 时间戳信息
    created_at: datetime = Field(default_factory=get_current_time, description="创建时间")
    uploaded_at: Optional[datetime] = Field(None, description="上传完成时间")
    verified_at: Optional[datetime] = Field(None, description="校验完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "file_12345",
                "upload_id": "upload_67890",
                "chunk_number": 1,
                "chunk_size": 5242880,
                "start_byte": 0,
                "end_byte": 5242879,
                "minio_object_name": "chunks/part-1",
                "minio_bucket": "foxmask",
                "status": "uploaded",
                "retry_count": 0
            }
        }
    )

    class Settings:
        """MongoDB集合配置"""
        name = "file_chunks"
        use_state_management = True
        validate_on_save = True
        
        # 索引配置
        indexes = [
            # 唯一复合索引 - 确保文件分片唯一性
            IndexModel(
                [("file_id", ASCENDING), ("chunk_number", ASCENDING)], 
                name="file_chunk_unique",
                unique=True
            ),
            
            # 上传会话查询索引
            IndexModel(
                [("upload_id", ASCENDING), ("status", ASCENDING)],
                name="upload_status"
            ),
            
            # 时间范围查询索引（用于清理和监控）
            IndexModel(
                [("created_at", DESCENDING)],
                name="created_at_desc"
            ),
        ]

    def mark_uploaded(self, etag: str, uploaded_at: datetime = None) -> None:
        """标记分片为已上传状态"""
        logger.debug(f"Marking chunk {self.chunk_number} of file {self.file_id} as uploaded")
        self.status = ChunkStatus.UPLOADED
        self.minio_etag = etag
        self.uploaded_at = uploaded_at or get_current_time()
        self.retry_count = 0
        self.error_message = None

    def mark_verified(self, verified_at: datetime = None) -> None:
        """标记分片为已校验状态"""
        logger.debug(f"Marking chunk {self.chunk_number} of file {self.file_id} as verified")
        self.status = ChunkStatus.VERIFIED
        self.verified_at = verified_at or get_current_time()
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """标记分片为失败状态"""
        logger.warning(f"Marking chunk {self.chunk_number} of file {self.file_id} as failed: {error_message}")
        self.status = ChunkStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1

    def is_completed(self) -> bool:
        """检查分片是否已完成上传"""
        return self.status in [ChunkStatus.UPLOADED, ChunkStatus.VERIFIED]

    def can_retry(self, max_retries: int = 3) -> bool:
        """检查分片是否可以重试"""
        return self.status == ChunkStatus.FAILED and self.retry_count < max_retries

    @classmethod
    async def bulk_mark_uploaded(cls, file_id: str, chunk_numbers: list, etag: str) -> Any:
        """批量标记分片为已上传状态"""
        logger.info(f"Bulk marking {len(chunk_numbers)} chunks of file {file_id} as uploaded")
        return await cls.find({
            "file_id": file_id,
            "chunk_number": {"$in": chunk_numbers}
        }).update_many({
            "$set": {
                "status": ChunkStatus.UPLOADED,
                "minio_etag": etag,
                "uploaded_at": get_current_time(),
                "retry_count": 0,
                "error_message": None
            }
        })

    @classmethod
    async def bulk_mark_verified(cls, file_id: str, chunk_numbers: list) -> Any:
        """批量标记分片为已校验状态"""
        logger.info(f"Bulk marking {len(chunk_numbers)} chunks of file {file_id} as verified")
        return await cls.find({
            "file_id": file_id,
            "chunk_number": {"$in": chunk_numbers}
        }).update_many({
            "$set": {
                "status": ChunkStatus.VERIFIED,
                "verified_at": get_current_time(),
                "error_message": None
            }
        })

    @classmethod
    async def find_by_file(cls, file_id: str, skip: int = 0, limit: int = 100) -> list:
        """根据文件ID查找分片列表"""
        logger.debug(f"Finding chunks for file {file_id}, skip={skip}, limit={limit}")
        return await cls.find({"file_id": file_id}).skip(skip).limit(limit).to_list()

    @classmethod
    async def find_by_file_and_status(cls, file_id: str, status: ChunkStatus) -> list:
        """根据文件ID和状态查找分片"""
        logger.debug(f"Finding chunks for file {file_id} with status {status}")
        return await cls.find({"file_id": file_id, "status": status}).to_list()

    @classmethod
    async def count_by_status(cls, file_id: str, status: ChunkStatus) -> int:
        """统计指定状态的分片数量"""
        logger.debug(f"Counting chunks for file {file_id} with status {status}")
        return await cls.find({"file_id": file_id, "status": status}).count()

    @classmethod
    async def get_upload_progress(cls, file_id: str) -> dict:
        """获取文件上传进度统计信息"""
        logger.debug(f"Getting upload progress for file {file_id}")
        
        total = await cls.find({"file_id": file_id}).count()
        uploaded = await cls.find({"file_id": file_id, "status": ChunkStatus.UPLOADED}).count()
        verified = await cls.find({"file_id": file_id, "status": ChunkStatus.VERIFIED}).count()
        failed = await cls.find({"file_id": file_id, "status": ChunkStatus.FAILED}).count()
        
        progress_data = {
            "total": total,
            "uploaded": uploaded,
            "verified": verified,
            "failed": failed,
            "completed": uploaded + verified,
            "progress": (uploaded + verified) / total * 100 if total > 0 else 0
        }
        
        logger.info(f"Upload progress for file {file_id}: {progress_data}")
        return progress_data

    @classmethod
    async def bulk_insert(cls, chunks: list) -> None:
        """批量插入分片数据"""
        if not chunks:
            logger.warning("Attempted to bulk insert empty chunks list")
            return
        
        try:
            await cls.insert_many(chunks)
            logger.info(f"Successfully inserted {len(chunks)} chunks using Beanie bulk insert")
        except Exception as e:
            logger.error(f"Failed to bulk insert chunks: {e}")
            raise


class File(Document):
    """
    文件模型
    管理文件的元数据、状态和访问控制信息
    """
    
    # 主标识字段
    filename: str = Field(..., min_length=1, max_length=255, description="原始文件名")
    
    # 文件属性
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    content_type: str = Field("application/octet-stream", description="文件内容类型")
    file_type: FileType = Field(FileType.UNKNOWN, description="文件类型分类")
    extension: str = Field("", description="文件扩展名")
    
    # 存储信息
    url: Optional[str] = Field(None, description="公开访问URL（如果可用）")
    minio_bucket: str = Field("foxmask", description="MinIO存储桶名称")
    minio_object_name: str = Field(..., description="MinIO对象名称")
    
    # 状态与进度
    status: FileStatus = Field(FileStatus.DRAFT, description="文件状态")
    upload_progress: float = Field(0.0, ge=0.0, le=100.0, description="上传进度百分比")
    
    # 校验和信息
    checksum_md5: Optional[str] = Field(None, description="完整文件的MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="完整文件的SHA256校验和")
    
    # 所有权与权限
    uploaded_by: str = Field(..., description="上传用户ID")
    tenant_id: str = Field(..., description="租户/组织ID")
    visibility: FileVisibility = Field(FileVisibility.PRIVATE, description="文件可见性级别")
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    
    # 元数据
    tags: List[str] = Field(default_factory=list, description="文件标签，用于分类")
    description: Optional[str] = Field(None, max_length=1000, description="文件描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    
    # 分片上传相关
    is_multipart: bool = Field(False, description="是否是多部分上传")
    upload_id: Optional[str] = Field(None, description="MinIO多部分上传会话ID")
    chunk_size: int = Field(5 * 1024 * 1024, description="分片大小（字节，默认5MB）")
    total_chunks: int = Field(0, ge=0, description="总分片数")
    uploaded_chunks: int = Field(0, ge=0, description="已上传分片数")
    verified_chunks: int = Field(0, ge=0, description="已校验分片数")
    
    # 时间戳信息
    created_at: datetime = Field(default_factory=get_current_time, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_time, description="最后更新时间")
    uploaded_at: Optional[datetime] = Field(None, description="上传完成时间")
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # 使用统计
    download_count: int = Field(0, ge=0, description="下载次数")
    view_count: int = Field(0, ge=0, description="查看次数")
    last_downloaded_at: Optional[datetime] = Field(None, description="最后下载时间")
    last_viewed_at: Optional[datetime] = Field(None, description="最后查看时间")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "example.pdf",
                "file_size": 1048576,
                "content_type": "application/pdf",
                "file_type": "pdf",
                "extension": "pdf",
                "minio_bucket": "foxmask",
                "minio_object_name": "20240101_12345678_abc123.pdf",
                "status": "uploaded",
                "uploaded_by": "user_123",
                "tenant_id": "tenant_456",
                "visibility": "private"
            }
        }
    )

    class Settings:
        """MongoDB集合配置"""
        name = "files"
        
        # 索引配置
        indexes = [
            # 单字段索引（用于经常查询的字段）
            IndexModel([("uploaded_by", ASCENDING)], name="uploaded_by"),
            IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
            IndexModel([("visibility", ASCENDING)], name="visibility"),
            IndexModel([("file_type", ASCENDING)], name="file_type"),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("created_at", ASCENDING)], name="created_at"),
            IndexModel([("updated_at", ASCENDING)], name="updated_at"),
            IndexModel([("expires_at", ASCENDING)], name="expires_at"),
            
            # 复合索引（用于常见查询组合）
            IndexModel([("tenant_id", ASCENDING), ("visibility", ASCENDING)], 
                      name="tenant_id_visibility"),
            IndexModel([("uploaded_by", ASCENDING), ("status", ASCENDING)], 
                      name="uploaded_by_status"),
            IndexModel([("tenant_id", ASCENDING), ("uploaded_by", ASCENDING)], 
                      name="tenant_id_uploaded_by"),
            
            # 多键索引（用于数组字段）
            IndexModel([("tags", ASCENDING)], name="tags"),
            IndexModel([("tags", ASCENDING), ("file_type", ASCENDING)], 
                      name="tags_file_type"),
            
            # TTL索引（用于自动过期文档）
            IndexModel([("expires_at", ASCENDING)], name="expires_at_ttl", 
                      expireAfterSeconds=0),
        ]

    @field_validator('extension', mode='before')
    @classmethod
    def extract_extension(cls, v, info) -> str:
        """从文件名中提取扩展名（如果未提供）"""
        if v:
            return v.lower()
        
        # 从数据中获取文件名
        data = getattr(info, 'data', {})
        filename = data.get('filename', '')
        
        if not filename or '.' not in filename:
            return ''
        
        # 处理复杂扩展名（如.tar.gz）
        parts = filename.rsplit('.', 2)
        if len(parts) > 2 and parts[-2].lower() == 'tar':
            return 'tar.gz'
        return parts[-1].lower()

    @model_validator(mode='after')
    def determine_file_type(self) -> 'File':
        """根据扩展名和内容类型确定文件类型"""
        if self.file_type != FileType.UNKNOWN:
            return self
        
        extension = self.extension.lower() if self.extension else ''
        content_type = self.content_type.lower() if self.content_type else ''
        
        # 优先使用扩展名查找
        if extension and f".{extension}" in EXTENSION_FILE_TYPES:
            self.file_type = EXTENSION_FILE_TYPES[f".{extension}"]
            logger.debug(f"Determined file type {self.file_type} from extension {extension}")
            return self
        
        # 回退到内容类型判断
        if any(x in content_type for x in ['pdf', 'document', 'msword', 'wordprocessing']):
            self.file_type = FileType.PDF if 'pdf' in content_type else FileType.DOCUMENT
        elif any(x in content_type for x in ['spreadsheet', 'excel']):
            self.file_type = FileType.SPREADSHEET
        elif any(x in content_type for x in ['presentation', 'powerpoint']):
            self.file_type = FileType.PRESENTATION
        elif any(x in content_type for x in ['text/', 'markdown']):
            self.file_type = FileType.TEXT
        elif content_type.startswith('image/'):
            self.file_type = FileType.IMAGE if 'svg' not in content_type else FileType.VECTOR
        elif content_type.startswith('audio/'):
            self.file_type = FileType.AUDIO
        elif content_type.startswith('video/'):
            self.file_type = FileType.VIDEO
        elif 'json' in content_type:
            self.file_type = FileType.JSON
        elif 'xml' in content_type:
            self.file_type = FileType.XML
        elif 'csv' in content_type:
            self.file_type = FileType.CSV
        elif any(x in content_type for x in ['zip', 'rar', 'tar', 'gzip', 'compress']):
            self.file_type = FileType.ARCHIVE
        
        logger.debug(f"Determined file type {self.file_type} from content type {content_type}")
        return self

    def to_response_dict(self) -> Dict[str, Any]:
        """转换为响应字典格式"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        data['id'] = str(self.id)
        return data

    def update_status(self, status: FileStatus) -> None:
        """更新文件状态"""
        logger.info(f"Updating file {self.id} status from {self.status} to {status}")
        self.status = status
        self.updated_at = get_current_time()

    def update_progress(self, uploaded: int, verified: int) -> None:
        """更新上传进度"""
        if uploaded > self.total_chunks or verified > self.total_chunks:
            error_msg = f"Uploaded ({uploaded}) or verified ({verified}) chunks exceed total ({self.total_chunks})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.uploaded_chunks = uploaded
        self.verified_chunks = verified
        
        if self.total_chunks > 0:
            self.upload_progress = (uploaded / self.total_chunks) * 100
        
        if uploaded == self.total_chunks and verified == self.total_chunks:
            self.status = FileStatus.UPLOADED
            self.uploaded_at = get_current_time()
            logger.info(f"File {self.id} upload completed successfully")
        elif uploaded > 0:
            self.status = FileStatus.UPLOADING
        
        logger.debug(f"File {self.id} progress updated: uploaded={uploaded}, verified={verified}, progress={self.upload_progress}%")

    def is_upload_complete(self) -> bool:
        """检查文件上传是否完成"""
        return (self.status in [FileStatus.UPLOADED, FileStatus.VERIFIED, FileStatus.COMPLETED] and
                self.uploaded_chunks == self.total_chunks and
                self.verified_chunks == self.total_chunks)

    def can_be_accessed_by(self, user_id: str, user_roles: List[str]) -> bool:
        """检查用户是否有权限访问此文件"""
        if self.visibility == FileVisibility.PUBLIC:
            return True
        if user_id == self.uploaded_by:
            return True
        if self.visibility == FileVisibility.TENANT:
            # TODO: 实现租户验证逻辑
            return True
        if user_id in self.allowed_users:
            return True
        if any(role in user_roles for role in self.allowed_roles):
            return True
        
        logger.warning(f"User {user_id} denied access to file {self.id}")
        return False

    def generate_minio_object_name(self) -> str:
        """生成MinIO对象名称"""
        if self.minio_object_name:
            return self.minio_object_name
        
        timestamp = int(get_current_time().timestamp())
        random_code = uuid.uuid4().hex[:8]
        extension = f".{self.extension}" if self.extension else ""
        object_name = f"{self.tenant_id}/{self.uploaded_by}/{timestamp}_{random_code}{extension}"
        
        logger.debug(f"Generated MinIO object name: {object_name}")
        return object_name

    def increment_download_count(self) -> None:
        """增加下载计数"""
        self.download_count += 1
        self.last_downloaded_at = get_current_time()
        self.updated_at = get_current_time()
        logger.info(f"File {self.id} download count incremented to {self.download_count}")

    def increment_view_count(self) -> None:
        """增加查看计数"""
        self.view_count += 1
        self.last_viewed_at = get_current_time()
        self.updated_at = get_current_time()
        logger.info(f"File {self.id} view count incremented to {self.view_count}")