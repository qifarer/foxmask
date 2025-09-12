# foxmask/document/schemas.py
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from .models import DocumentSourceType, WebSourceDetails, ApiSourceDetails, FileSourceDetails, TextSourceDetails

class DocumentStatus(str, Enum):
    CREATING = "creating"
    CREATED = "created"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

# 请求Schemas
class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文档标题")
    description: str = Field(..., min_length=1, max_length=1000, description="文档描述")
    source_type: DocumentSourceType = Field(..., description="文档来源类型")
    source_details: Optional[Union[WebSourceDetails, ApiSourceDetails, FileSourceDetails, TextSourceDetails]] = Field(
        None, description="来源详细信息"
    )
    file_ids: List[str] = Field(..., min_items=1, description="关联文件ID列表")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

    @validator('source_details')
    def validate_source_details(cls, v, values):
        source_type = values.get('source_type')
        if source_type and v:
            expected_type = {
                DocumentSourceType.WEB: WebSourceDetails,
                DocumentSourceType.API: ApiSourceDetails,
                DocumentSourceType.FILE: FileSourceDetails,
                DocumentSourceType.TEXT: TextSourceDetails
            }.get(source_type)
            if not isinstance(v, expected_type):
                raise ValueError(f"Source details must be of type {expected_type.__name__} for source type {source_type}")
        return v

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="文档标题")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, description="文档描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    tags: Optional[List[str]] = Field(None, description="标签列表")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ContentCreate(BaseModel):
    document_id: str = Field(..., description="关联文档ID")
    raw_text: Optional[str] = Field(None, description="原始文本内容")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="结构化数据")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="内容元数据")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="文件名称")
    original_name: str = Field(..., min_length=1, max_length=255, description="原始文件名")
    size: int = Field(..., ge=0, description="文件大小（字节）")
    mime_type: str = Field(..., description="MIME类型")
    storage_path: str = Field(..., description="存储路径")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="文件元数据")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# 响应Schemas
class DocumentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: DocumentStatus
    source_type: DocumentSourceType
    source_uri: Optional[str]
    file_ids: List[str]
    processed_file_ids: Optional[List[str]] = None
    owner: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        use_enum_values=True
    )

class DocumentDetailResponse(DocumentResponse):
    source_details: Optional[Union[WebSourceDetails, ApiSourceDetails, FileSourceDetails, TextSourceDetails]] = None
    metadata: Dict[str, Any]
    processing_stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        use_enum_values=True
    )

class ContentResponse(BaseModel):
    id: str
    document_id: str
    raw_text: Optional[str]
    structured_data: Optional[Dict[str, Any]]
    word_count: Optional[int]
    language: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileResponse(BaseModel):
    id: str
    name: str
    original_name: str
    size: int
    mime_type: str
    status: str
    owner: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileDetailResponse(FileResponse):
    storage_path: str
    metadata: Dict[str, Any]
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# 聚合响应Schemas
class DocumentWithContentResponse(DocumentDetailResponse):
    content: Optional[ContentResponse] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class DocumentWithFilesResponse(DocumentDetailResponse):
    files: List[FileResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FullDocumentResponse(DocumentDetailResponse):
    content: Optional[ContentResponse] = None
    files: List[FileResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# 分页和列表Schemas
class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(100, ge=1, le=1000, description="每页记录数")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ContentListResponse(BaseModel):
    items: List[ContentResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileListResponse(BaseModel):
    items: List[FileResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# 状态更新Schemas
class StatusUpdate(BaseModel):
    status: DocumentStatus
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ContentStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# 搜索和过滤Schemas
class DocumentFilter(BaseModel):
    status: Optional[DocumentStatus] = None
    source_type: Optional[DocumentSourceType] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class DocumentSearch(BaseModel):
    query: Optional[str] = None
    filter: Optional[DocumentFilter] = None
    pagination: PaginationParams = Field(default_factory=PaginationParams)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )