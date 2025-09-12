# foxmask/file/models.py
from enum import Enum
from datetime import datetime, timezone
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from bson import ObjectId
from uuid import UUID, uuid4
import re

class FileStatus(str, Enum):
    """文件状态枚举"""
    UPLOADING = "uploading"      # 上传中
    UPLOADED = "uploaded"        # 已上传
    PROCESSING = "processing"    # 处理中
    PROCESSED = "processed"      # 已处理
    ARCHIVED = "archived"        # 已归档
    DELETED = "deleted"          # 已删除
    ERROR = "error"              # 错误

class FileType(str, Enum):
    """文件类型枚举"""
    DOCUMENT = "document"        # 文档
    IMAGE = "image"              # 图片
    VIDEO = "video"              # 视频
    AUDIO = "audio"              # 音频
    ARCHIVE = "archive"          # 压缩包
    CODE = "code"                # 代码文件
    DATA = "data"                # 数据文件
    OTHER = "other"              # 其他

class StorageProvider(str, Enum):
    """存储提供商枚举"""
    MINIO = "minio"              # MinIO存储
    S3 = "s3"                    # AWS S3
    AZURE = "azure"              # Azure Blob Storage
    GCS = "gcs"                  # Google Cloud Storage
    LOCAL = "local"              # 本地存储

class File(Document):
    """文件核心实体"""
    # Pydantic V2 配置
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
            UUID: lambda v: str(v),
        }
    )
    
    # Beanie 2.0.0 使用 PydanticObjectId 作为主键
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    
    # 业务标识
    file_id: UUID = Field(default_factory=uuid4, description="文件业务ID")
    
    # 文件基本信息
    filename: str = Field(..., max_length=255, description="文件名")
    original_filename: str = Field(..., max_length=255, description="原始文件名")
    size: int = Field(..., ge=0, description="文件大小（字节）")
    content_type: str = Field(..., max_length=100, description="内容类型")
    extension: str = Field(..., max_length=20, description="文件扩展名")
    file_type: FileType = Field(..., description="文件类型")
    
    # 存储信息
    storage_provider: StorageProvider = Field(default=StorageProvider.MINIO, description="存储提供商")
    bucket_name: str = Field(..., max_length=100, description="存储桶名称")
    object_key: str = Field(..., max_length=500, description="对象键")
    storage_class: str = Field(default="STANDARD", max_length=50, description="存储类别")
    checksum: Optional[str] = Field(None, max_length=64, description="文件校验和")
    encryption_key: Optional[str] = Field(None, max_length=256, description="加密密钥")
    
    # 状态信息
    status: FileStatus = Field(default=FileStatus.UPLOADING, description="文件状态")
    error_message: Optional[str] = Field(None, max_length=1000, description="错误信息")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    
    # 处理信息
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list, description="处理步骤")
    processed_by: Optional[str] = Field(None, max_length=100, description="处理器")
    
    # 权限控制
    owner_id: str = Field(..., max_length=50, description="所有者ID")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    project_id: Optional[str] = Field(None, max_length=50, description="项目ID")
    is_public: bool = Field(default=False, description="是否公开")
    access_control: Dict[str, List[str]] = Field(default_factory=dict, description="访问控制列表")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tags: List[str] = Field(default_factory=list, description="标签")
    categories: List[str] = Field(default_factory=list, description="分类")
    
    # 版本控制
    version: int = Field(default=1, ge=1, description="版本号")
    previous_version: Optional[PydanticObjectId] = Field(None, description="上一个版本ID")
    is_latest: bool = Field(default=True, description="是否最新版本")
    
    # 时间戳
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="上传时间")
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")
    accessed_at: Optional[datetime] = Field(None, description="最后访问时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # 软删除支持
    is_deleted: bool = Field(default=False, description="是否删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    
    # Beanie 2.0.0 设置
    class Settings:
        name = "files"
        use_state_management = True
        use_revision = False
        validate_on_save = True
    
    @field_validator('extension', mode='before')
    @classmethod
    def validate_extension(cls, v):
        """验证文件扩展名"""
        if v and not v.startswith('.'):
            v = '.' + v
        return v.lower() if v else v
    
    @field_validator('filename', mode='before')
    @classmethod
    def validate_filename(cls, v):
        """验证文件名"""
        if v:
            # 移除非法字符
            v = re.sub(r'[<>:"/\\|?*]', '_', v)
            return v.strip()
        return v
    
    @field_validator('file_id', mode='before')
    @classmethod
    def validate_file_id(cls, v):
        """确保file_id是UUID"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError("Invalid UUID format")
        return v
    
    def update_timestamp(self):
        """更新时间戳"""
        self.uploaded_at = datetime.now(timezone.utc)
    
    def add_processing_step(self, step_name: str, status: str, details: Dict[str, Any] = None):
        """添加处理步骤记录"""
        step = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {}
        }
        self.processing_steps.append(step)
        self.update_timestamp()
    
    def mark_as_processed(self, processed_by: Optional[str] = None):
        """标记为已处理"""
        self.status = FileStatus.PROCESSED
        self.processed_at = datetime.now(timezone.utc)
        if processed_by:
            self.processed_by = processed_by
        self.update_timestamp()
    
    def mark_as_deleted(self):
        """标记为软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.status = FileStatus.DELETED
        self.update_timestamp()
    
    def increment_retry(self):
        """增加重试计数"""
        self.retry_count += 1
        self.update_timestamp()

class FileChunk(Document):
    """文件分块实体（用于大文件分块上传）"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }
    )
    
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    
    # 分块信息
    file_id: PydanticObjectId = Field(..., description="文件ID")
    chunk_number: int = Field(..., ge=0, description="分块编号")
    chunk_size: int = Field(..., ge=0, description="分块大小")
    total_chunks: int = Field(..., ge=1, description="总分块数")
    
    # 存储信息
    storage_provider: StorageProvider = Field(..., description="存储提供商")
    bucket_name: str = Field(..., max_length=100, description="存储桶名称")
    object_key: str = Field(..., max_length=500, description="对象键")
    
    # 校验信息
    checksum: str = Field(..., max_length=64, description="分块校验和")
    is_uploaded: bool = Field(default=False, description="是否已上传")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uploaded_at: Optional[datetime] = Field(None, description="上传时间")
    
    class Settings:
        name = "file_chunks"
        use_state_management = True
        use_revision = False

class FileVersion(Document):
    """文件版本实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }
    )
    
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    
    # 版本信息
    file_id: PydanticObjectId = Field(..., description="文件ID")
    version: int = Field(..., ge=1, description="版本号")
    description: Optional[str] = Field(None, max_length=500, description="版本描述")
    
    # 文件信息
    filename: str = Field(..., max_length=255, description="文件名")
    size: int = Field(..., ge=0, description="文件大小")
    content_type: str = Field(..., max_length=100, description="内容类型")
    
    # 存储信息
    storage_provider: StorageProvider = Field(..., description="存储提供商")
    bucket_name: str = Field(..., max_length=100, description="存储桶名称")
    object_key: str = Field(..., max_length=500, description="对象键")
    
    # 创建信息
    created_by: str = Field(..., max_length=50, description="创建者")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "file_versions"
        use_state_management = True
        use_revision = False

class FileAccessLog(Document):
    """文件访问日志实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }
    )
    
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    
    # 访问信息
    file_id: PydanticObjectId = Field(..., description="文件ID")
    user_id: str = Field(..., max_length=50, description="用户ID")
    action: str = Field(..., max_length=50, description="操作类型")  # read, download, preview, etc.
    
    # 访问上下文
    ip_address: Optional[str] = Field(None, max_length=45, description="IP地址")
    user_agent: Optional[str] = Field(None, max_length=500, description="用户代理")
    referrer: Optional[str] = Field(None, max_length=500, description="来源")
    
    # 访问结果
    success: bool = Field(default=True, description="是否成功")
    error_message: Optional[str] = Field(None, max_length=1000, description="错误信息")
    
    # 时间戳
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "file_access_logs"
        use_state_management = True
        use_revision = False