# foxmask/file/dto/upload.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from foxmask.file.enums import UploadSourceTypeEnum, UploadStrategyEnum, UploadTaskTypeEnum
from foxmask.file.enums import FileTypeEnum
from foxmask.core.model import Status

class UploadTaskFileChunkDTO(BaseModel):
    """上传分块DTO"""
    
    task_id: str = Field(..., description="任务ID")
    file_id: str = Field(..., description="文件ID")
    chunk_number: int = Field(..., ge=1, description="分块编号")
    chunk_data: bytes = Field(..., description="分块数据")
    chunk_size: int = Field(..., ge=0, description="分块大小")
    is_final_chunk: bool = Field(default=False, description="是否为最后分块")
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")

class UploadTaskFileDTO(BaseModel):
    """上传文件信息DTO"""
    filename: str = Field(..., description="文件名")
    original_path: str = Field(..., description="原始文件路径")
    storage_path: str = Field(..., description="存储路径")
    file_size: int = Field(..., ge=0, description="文件大小")
    file_type: FileTypeEnum = Field(default=FileTypeEnum.OTHER, description="文件类型")
    content_type: str = Field(default="application/octet-stream", description="内容类型")
    extension: str = Field(..., description="文件扩展名")
    checksum_md5: Optional[str] = Field(None, description="MD5校验和")
    checksum_sha256: Optional[str] = Field(None, description="SHA256校验和")
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict, description="自动提取的元数据")


class UploadTaskInitDTO(BaseModel):
    """上传任务初始化DTO - 包含任务和文件信息"""
    tenant_id: Optional[str] = 'foxmask'
    created_by: Optional[str] = None
    # 任务基础信息
    source_type: UploadSourceTypeEnum = Field(..., description="上传源类型")
    title: str = Field(..., min_length=1, max_length=300, description="任务标题")
    desc: Optional[str] = Field(None, description="任务描述")
    
    # 上传配置
    upload_strategy: UploadStrategyEnum = Field(default=UploadStrategyEnum.PARALLEL, description="上传策略")
    max_parallel_uploads: int = Field(default=5, ge=1, le=50, description="最大并行上传数")
    chunk_size: int = Field(default=10 * 1024 * 1024, ge=1 * 1024 * 1024, description="分块大小")
    
    # 目录处理
    preserve_structure: bool = Field(default=True, description="是否保持目录结构")
    base_upload_path: Optional[str] = Field(None, description="基础上传路径")
    
    # 自动元数据提取
    auto_extract_metadata: bool = Field(default=True, description="是否自动提取元数据")
    file_type_filters: List[FileTypeEnum] = Field(default_factory=list, description="文件类型过滤器")
    max_file_size: Optional[int] = Field(None, ge=0, description="最大文件大小限制")
    
    # 文件信息
    files: List[UploadTaskFileDTO] = Field(..., min_items=1, description="文件信息列表")
    

class UploadTaskCompleteDTO(BaseModel):
    """上传任务完成DTO"""
    
    task_id: str = Field(..., description="任务ID")
    force_complete: bool = Field(default=False, description="强制完成（即使有失败文件）")

class UploadTaskQueryDTO(BaseModel):
    """上传任务查询DTO"""
    
    source_type: Optional[UploadSourceTypeEnum] = Field(None, description="上传源类型")
    status: Optional[Status] = Field(None, description="任务状态")
    created_by: Optional[str] = Field(None, description="创建者")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
