from enum import Enum
from datetime import datetime, timezone
from beanie import Document, Indexed, Link, BackLink
from pydantic import Field, HttpUrl, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Set, ClassVar
from bson import ObjectId
from decimal import Decimal
from typing_extensions import Annotated  # 用于更复杂的字段类型
from foxmask.tag.models import Tag

class KnowledgeType(str, Enum):
    FILE = "file"
    WEBPAGE = "webpage"
    API = "api"
    CHAT = "chat"
    STRUCTURED = "structured"
    PRODUCT = "product"
    CATEGORY = "category"
    BRAND = "brand"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    DATABASE = "database"
    KNOWLEDGE_BASE = "knowledge_base"
    OTHER = "other"

class SourceType(str, Enum):
    FILE = "file"
    WEBPAGE = "webpage"
    API = "api"
    CHAT = "chat"
    STRUCTURED = "structured"
    PRODUCT = "product"
    BRAND = "brand"

class ItemStatus(str, Enum):
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VECTORIZING = "vectorizing"
    VECTORIZED = "vectorized"
    GRAPH_PROCESSING = "graph_processing"
    COMPLETED = "completed"
    ERROR = "error"

class AccessLevel(str, Enum):
    PUBLIC = "public"       # 公开访问
    TENANT = "tenant"       # 租户内访问
    USER = "user"           # 仅创建用户访问
    PRIVATE = "private"     # 私有（需要特定权限）

class ContentType(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    XML = "xml"

class KnowledgeItem(Document):
    # Pydantic V2 配置
    model_config = ConfigDict(
        populate_by_name=True,  # 允许使用字段名和别名
        arbitrary_types_allowed=True,  # 允许任意类型（如ObjectId）
        validate_assignment=True,  # 赋值时验证
        use_enum_values=True,      # 使用枚举值而不是枚举对象
    )
    
    # MongoDB ObjectId作为主键
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    
    # 基本信息
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    summary: Optional[str] = Field(None, max_length=2000)
    
    # 分类信息
    source_type: SourceType
    knowledge_type: KnowledgeType
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    
    # 来源信息
    sources: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    original_format: Optional[str] = Field(None, max_length=50)
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    language: str = Field(default="zh-CN", max_length=10)
    version: int = Field(default=1, ge=1)
    
    # 内容引用
    content_refs: Dict[ContentType, str] = Field(default_factory=dict)
    
    # 处理状态
    status: ItemStatus = Field(default=ItemStatus.CREATED)
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = Field(None, max_length=1000)
    retry_count: int = Field(default=0, ge=0)
    
    # 权限控制
    access_level: AccessLevel = Field(default=AccessLevel.USER)
    tenant_id: Optional[str] = Field(None, max_length=50)
    created_by: str = Field(..., max_length=50)
    updated_by: str = Field(..., max_length=50)
    
    # 关联关系 - 使用Link进行关联
    tag_refs: List[Link["Tag"]] = Field(default_factory=list)
    knowledge_bases: List[Link["KnowledgeBase"]] = Field(default_factory=list)
    related_items: List[Link["KnowledgeItem"]] = Field(default_factory=list)
    
    # 向量和图谱
    vector_id: Optional[str] = Field(None, max_length=100)
    graph_id: Optional[str] = Field(None, max_length=100)
    embedding_model: Optional[str] = Field(None, max_length=50)
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    # 软删除支持
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    class Settings:
        name = "knowledge_items"
        indexes = [
            # 单字段索引
            "title",
            "source_type",
            "knowledge_type",
            "status",
            "access_level",
            "created_by",
            "created_at",
            "is_deleted",
            # 复合索引
            [("tenant_id", 1), ("access_level", 1)],
            [("created_by", 1), ("access_level", 1)],
            [("status", 1), ("retry_count", 1)],
            [("knowledge_type", 1), ("category", 1)],
            # 文本索引，支持全文搜索
            [("title", "text"), ("description", "text"), ("summary", "text")],
            # TTL索引，用于自动清理旧数据
            [("created_at", 1), ("expireAfterSeconds", 3600)]
        ]
    
    @field_validator('source_urls', mode='before')
    @classmethod
    def validate_source_urls(cls, v):
        """将HttpUrl转换为字符串"""
        if isinstance(v, list):
            return [str(url) if hasattr(url, '__str__') else url for url in v]
        return v
    
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
    
    def add_processing_step(self, step_name: str, status: str, details: Dict[str, Any] = None):
        """添加处理步骤记录"""
        step = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {}
        }
        self.processing_steps.append(step)
    
    def mark_as_deleted(self):
        """标记为软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.update_timestamp()

class KnowledgeContent(Document):
    """知识内容实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
    )
    
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    
    # 关联的知识条目ID
    item_id: Link[KnowledgeItem]
    content_type: ContentType
    
    # 内容数据
    content_text: Optional[str] = Field(None, max_length=16000)
    content_ref: Optional[str] = Field(None, max_length=500)
    
    # 内容元数据
    content_size: int = Field(default=0, ge=0)
    encoding: str = Field(default="utf-8", max_length=20)
    checksum: Optional[str] = Field(None, max_length=64)
    
    # 处理信息
    parser_version: Optional[str] = Field(None, max_length=20)
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_keywords: List[str] = Field(default_factory=list)
    
    # 权限控制
    access_level: AccessLevel
    tenant_id: Optional[str] = Field(None, max_length=50)
    created_by: str = Field(..., max_length=50)
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # 软删除
    is_deleted: bool = Field(default=False)
    
    class Settings:
        name = "knowledge_contents"
        indexes = [
            "item_id",
            "content_type",
            "access_level",
            "tenant_id",
            "created_by",
            "created_at",
            "is_deleted",
            [("item_id", 1), ("content_type", 1)],
            [("tenant_id", 1), ("access_level", 1)],
            [("content_size", 1)],
            [("created_at", 1), ("expireAfterSeconds", 7200)]
        ]
    
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

class KnowledgeBase(Document):
    """知识库实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
    )
    
    id: Optional[ObjectId] = Field(default_factory=ObjectId, alias="_id")
    
    # 基本信息
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)
    
    # 分类信息
    category: Optional[str] = Field(None, max_length=100)
    base_type: str = Field(default="general", max_length=50)
    
    # 权限控制
    access_level: AccessLevel = Field(default=AccessLevel.USER)
    tenant_id: Optional[str] = Field(None, max_length=50)
    created_by: str = Field(..., max_length=50)
    collaborators: List[str] = Field(default_factory=list)
    
    # 内容统计
    item_count: int = Field(default=0, ge=0)
    total_size: int = Field(default=0, ge=0)
    
    # 关联关系
    items: List[Link[KnowledgeItem]] = Field(default_factory=list)
    tag_refs: List[Link["Tag"]] = Field(default_factory=list)
    parent_base: Optional[Link["KnowledgeBase"]] = None
    child_bases: List[Link["KnowledgeBase"]] = Field(default_factory=list)
    
    # 配置
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: Optional[datetime] = None
    
    # 软删除
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    class Settings:
        name = "knowledge_bases"
        indexes = [
            "name",
            "access_level",
            "tenant_id",
            "created_by",
            "category",
            "created_at",
            "is_active",
            "is_deleted",
            [("tenant_id", 1), ("access_level", 1)],
            [("created_by", 1), ("access_level", 1)],
            [("is_active", 1), ("item_count", 1)],
            [("name", "text"), ("description", "text")],
            [("created_at", 1), ("expireAfterSeconds", 86400)]
        ]
        
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now(timezone.utc)
        self.update_timestamp()
    
    def add_item(self, item: KnowledgeItem):
        """添加知识条目"""
        if item.id not in [i.id for i in self.items]:
            self.items.append(item)
            self.item_count += 1
            self.update_activity()
    
    def remove_item(self, item: KnowledgeItem):
        """移除知识条目"""
        self.items = [i for i in self.items if i.id != item.id]
        self.item_count = len(self.items)
        self.update_activity()
    
    def mark_as_deleted(self):
        """标记为软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False
        self.update_timestamp()