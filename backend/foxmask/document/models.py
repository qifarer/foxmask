# foxmask/document/models.py
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import uuid

class DocumentSourceType(str, Enum):
    FILE = "file"
    WEB = "web"
    API = "api"
    TEXT = "text"

class ContentStatus(str, Enum):
    RAW = "raw"
    PARSING = "parsing"
    PARSED = "parsed"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class FileStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class DocumentStatus(str, Enum):
    CREATING = "creating"
    CREATED = "created"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class WebSourceDetails(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    fetched_at: Optional[datetime] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ApiSourceDetails(BaseModel):
    endpoint: str
    api_name: str
    parameters: Optional[Dict[str, Any]] = None
    response_format: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FileSourceDetails(BaseModel):
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    storage_path: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class TextSourceDetails(BaseModel):
    content: str
    language: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ProcessingStats(BaseModel):
    parsing_time_ms: Optional[int] = None
    file_count: Optional[int] = None
    successful_files: Optional[int] = None
    failed_files: Optional[int] = None
    total_words: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class ParsedContent(BaseModel):
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    sections: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    parsed_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

# MongoDB文档模型
class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: DocumentStatus = DocumentStatus.CREATING
    
    # 来源信息
    source_type: DocumentSourceType
    source_details: Optional[Union[WebSourceDetails, ApiSourceDetails, FileSourceDetails, TextSourceDetails]] = None
    source_uri: Optional[str] = None
    
    # 关系引用
    content_id: Optional[str] = None
    file_ids: List[str] = Field(default_factory=list)
    processed_file_ids: Optional[List[str]] = None
    
    # 版本历史
    content_history: List[str] = Field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    # 所有权和时间
    owner: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 处理信息
    processing_stats: Optional[ProcessingStats] = None
    retry_count: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        use_enum_values=True
    )

class Content(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    raw_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    sections: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    status: ContentStatus = ContentStatus.RAW
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        use_enum_values=True
    )

class File(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    original_name: str
    size: int
    mime_type: str
    storage_path: str
    status: FileStatus = FileStatus.UPLOADING
    metadata: Dict[str, Any] = Field(default_factory=dict)
    owner: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        use_enum_values=True
    )

class DocumentFileRelation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    file_id: str
    relation_type: str = "primary"
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        use_enum_values=True
    )