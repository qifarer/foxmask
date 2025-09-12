from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from uuid import UUID
from .models import FileStatus, FileType, StorageProvider

class FileMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    date: str = Field(..., description="文件日期")
    dirname: str = Field(..., description="目录名称")
    filename: str = Field(..., description="文件名称")
    path: str = Field(..., description="文件路径")

class FileUploadState(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    progress: float = Field(..., ge=0, le=100, description="上传进度百分比")
    rest_time: float = Field(..., ge=0, description="剩余时间（秒）")
    speed: float = Field(..., ge=0, description="上传速度（字节/秒）")

class UploadBase64ToS3Result(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    file_type: str = Field(..., description="文件类型")
    hash: str = Field(..., description="文件哈希值")
    metadata: FileMetadata = Field(..., description="文件元数据")
    size: int = Field(..., ge=0, description="文件大小")

class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    data: Optional[FileMetadata] = Field(None, description="文件元数据")
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="消息")

class PreSignedUrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    pre_sign_url: str = Field(..., description="预签名URL")
    metadata: FileMetadata = Field(..., description="文件元数据")
    expires_in: int = Field(3600, description="过期时间（秒）")

class FileCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255, description="文件名称")
    file_type: FileType = Field(..., description="文件类型")
    hash: str = Field(..., max_length=64, description="文件哈希值")
    size: int = Field(..., ge=0, description="文件大小（字节）")
    url: str = Field(..., description="文件URL")
    metadata: FileMetadata = Field(..., description="文件元数据")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: bool = Field(False, description="是否公开")

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="文件ID")
    file_id: UUID = Field(..., description="文件业务ID")
    name: str = Field(..., description="文件名称")
    original_filename: str = Field(..., description="原始文件名")
    file_type: FileType = Field(..., description="文件类型")
    content_type: str = Field(..., description="内容类型")
    extension: str = Field(..., description="文件扩展名")
    size: int = Field(..., description="文件大小")
    hash: Optional[str] = Field(None, description="文件哈希值")
    url: str = Field(..., description="文件URL")
    status: FileStatus = Field(..., description="文件状态")
    storage_provider: StorageProvider = Field(..., description="存储提供商")
    bucket_name: str = Field(..., description="存储桶名称")
    object_key: str = Field(..., description="对象键")
    owner_id: str = Field(..., description="所有者ID")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    is_public: bool = Field(..., description="是否公开")
    metadata: Dict[str, Any] = Field(..., description="元数据")
    tags: List[str] = Field(..., description="标签列表")
    version: int = Field(..., description="版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    accessed_at: Optional[datetime] = Field(None, description="最后访问时间")

class CheckFileHashResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    is_exist: bool = Field(..., description="文件是否存在")
    metadata: Optional[FileMetadata] = Field(None, description="文件元数据")
    url: Optional[str] = Field(None, description="文件URL")
    file_id: Optional[str] = Field(None, description="文件ID")

class UploadWithProgressResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="文件ID")
    url: str = Field(..., description="文件URL")
    dimensions: Optional[Dict[str, int]] = Field(None, description="图片尺寸")
    filename: Optional[str] = Field(None, description="文件名称")
    file_type: Optional[str] = Field(None, description="文件类型")
    size: Optional[int] = Field(None, description="文件大小")

class UploadStatusUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="上传ID")
    type: str = Field(..., description="状态类型")
    value: Optional[Dict[str, Any]] = Field(None, description="状态值")

class FileListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    files: List[FileResponse] = Field(..., description="文件列表")
    total: int = Field(..., ge=0, description="总数")
    skip: int = Field(..., ge=0, description="跳过数量")
    limit: int = Field(..., ge=1, le=1000, description="每页数量")

class UploadFileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    directory: Optional[str] = Field(None, description="目录路径")
    pathname: Optional[str] = Field(None, description="完整路径")
    skip_check_file_type: bool = Field(False, description="跳过文件类型检查")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: bool = Field(False, description="是否公开")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    project_id: Optional[str] = Field(None, description="项目ID")

class UploadBase64Request(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    base64_data: str = Field(..., description="Base64编码的数据")
    filename: Optional[str] = Field(None, description="文件名称")
    directory: Optional[str] = Field(None, description="目录路径")
    pathname: Optional[str] = Field(None, description="完整路径")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: bool = Field(False, description="是否公开")

class UploadDataRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    data: Dict[str, Any] = Field(..., description="文件数据")
    filename: Optional[str] = Field(None, description="文件名称")
    directory: Optional[str] = Field(None, description="目录路径")
    pathname: Optional[str] = Field(None, description="完整路径")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: bool = Field(False, description="是否公开")

class PresignedUrlRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    filename: str = Field(..., min_length=1, description="文件名称")
    directory: Optional[str] = Field(None, description="目录路径")
    pathname: Optional[str] = Field(None, description="完整路径")
    content_type: Optional[str] = Field(None, description="内容类型")
    expires_in: int = Field(3600, ge=60, le=604800, description="过期时间（秒）")

class UploadWithProgressRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")
    skip_check_file_type: bool = Field(False, description="跳过文件类型检查")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: bool = Field(False, description="是否公开")

class FileUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="文件名称")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: Optional[bool] = Field(None, description="是否公开")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class FileSearchRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    query: Optional[str] = Field(None, description="搜索查询")
    file_type: Optional[FileType] = Field(None, description="文件类型")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: Optional[bool] = Field(None, description="是否公开")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(100, ge=1, le=1000, description="每页数量")

class FileChunkUploadRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    file_id: str = Field(..., description="文件ID")
    chunk_number: int = Field(..., ge=0, description="分块编号")
    total_chunks: int = Field(..., ge=1, description="总分块数")
    chunk_size: int = Field(..., ge=0, description="分块大小")

class FileChunkUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(..., description="是否成功")
    chunk_number: int = Field(..., description="分块编号")
    uploaded_size: int = Field(..., description="已上传大小")
    total_size: int = Field(..., description="总大小")

class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="消息")
    data: Optional[Any] = Field(None, description="数据")
    error_code: Optional[str] = Field(None, description="错误代码")

class PaginatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    items: List[Any] = Field(..., description="数据列表")