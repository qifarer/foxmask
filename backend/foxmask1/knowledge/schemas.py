from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import KnowledgeType, SourceType, ItemStatus, AccessLevel, ContentType
from uuid import UUID
from bson import ObjectId

class KnowledgeItemSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    # 核心标识
    id: str = Field(..., description="条目ID")
    title: str = Field(..., max_length=200, description="标题")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    summary: Optional[str] = Field(None, max_length=2000, description="摘要")
    
    # 分类信息
    source_type: SourceType = Field(..., description="来源类型")
    knowledge_type: KnowledgeType = Field(..., description="知识类型")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    subcategory: Optional[str] = Field(None, max_length=100, description="子分类")
    
    # 来源信息
    sources: List[str] = Field(default_factory=list, description="来源列表")
    source_urls: List[str] = Field(default_factory=list, description="来源URL")
    original_format: Optional[str] = Field(None, max_length=50, description="原始格式")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    language: str = Field(default="zh-CN", max_length=10, description="语言")
    version: int = Field(default=1, ge=1, description="版本")
    
    # 内容引用
    content_refs: Dict[ContentType, str] = Field(default_factory=dict, description="内容引用")
    
    # 处理状态
    status: ItemStatus = Field(..., description="状态")
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list, description="处理步骤")
    error_message: Optional[str] = Field(None, max_length=1000, description="错误信息")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    
    # 权限控制
    access_level: AccessLevel = Field(..., description="访问级别")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    created_by: str = Field(..., max_length=50, description="创建者")
    updated_by: str = Field(..., max_length=50, description="更新者")
    
    # 关联关系
    tag_refs: List[str] = Field(default_factory=list, description="标签引用")
    knowledge_bases: List[str] = Field(default_factory=list, description="知识库引用")
    related_items: List[str] = Field(default_factory=list, description="相关条目")
    
    # 向量和图谱
    vector_id: Optional[str] = Field(None, max_length=100, description="向量ID")
    graph_id: Optional[str] = Field(None, max_length=100, description="图谱ID")
    embedding_model: Optional[str] = Field(None, max_length=50, description="嵌入模型")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    processed_at: Optional[datetime] = Field(None, description="处理完成时间")
    
    # 软删除状态
    is_deleted: bool = Field(default=False, description="是否删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")

class KnowledgeBaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    # 核心标识
    id: str = Field(..., description="知识库ID")
    name: str = Field(..., max_length=100, description="名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    cover_image: Optional[str] = Field(None, max_length=500, description="封面图片")
    
    # 分类信息
    category: Optional[str] = Field(None, max_length=100, description="分类")
    base_type: str = Field(default="general", max_length=50, description="类型")
    
    # 权限控制
    access_level: AccessLevel = Field(..., description="访问级别")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    created_by: str = Field(..., max_length=50, description="创建者")
    collaborators: List[str] = Field(default_factory=list, description="协作者")
    
    # 内容统计
    item_count: int = Field(default=0, ge=0, description="条目数量")
    total_size: int = Field(default=0, ge=0, description="总大小")
    
    # 关联关系
    items: List[str] = Field(default_factory=list, description="条目列表")
    tag_refs: List[str] = Field(default_factory=list, description="标签引用")
    parent_base: Optional[str] = Field(None, description="父知识库")
    child_bases: List[str] = Field(default_factory=list, description="子知识库")
    
    # 配置
    settings: Dict[str, Any] = Field(default_factory=dict, description="设置")
    is_active: bool = Field(default=True, description="是否活跃")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")
    
    # 软删除状态
    is_deleted: bool = Field(default=False, description="是否删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")

class KnowledgeContentSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: str = Field(..., description="内容ID")
    item_id: str = Field(..., description="条目ID")
    content_type: ContentType = Field(..., description="内容类型")
    
    # 内容数据
    content_text: Optional[str] = Field(None, max_length=16000, description="文本内容")
    content_ref: Optional[str] = Field(None, max_length=500, description="内容引用")
    
    # 内容元数据
    content_size: int = Field(..., ge=0, description="内容大小")
    encoding: str = Field(default="utf-8", max_length=20, description="编码")
    checksum: Optional[str] = Field(None, max_length=64, description="校验和")
    
    # 处理信息
    parser_version: Optional[str] = Field(None, max_length=20, description="解析器版本")
    extracted_entities: List[Dict[str, Any]] = Field(default_factory=list, description="提取实体")
    extracted_keywords: List[str] = Field(default_factory=list, description="提取关键词")
    
    # 权限控制
    access_level: AccessLevel = Field(..., description="访问级别")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    created_by: str = Field(..., max_length=50, description="创建者")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 软删除状态
    is_deleted: bool = Field(default=False, description="是否删除")

class KnowledgeItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    source_type: SourceType = Field(..., description="来源类型")
    knowledge_type: KnowledgeType = Field(..., description="知识类型")
    sources: List[str] = Field(default_factory=list, description="来源列表")
    source_urls: Optional[List[str]] = Field(None, description="来源URL")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    subcategory: Optional[str] = Field(None, max_length=100, description="子分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    knowledge_bases: Optional[List[str]] = Field(None, description="知识库列表")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    access_level: AccessLevel = Field(default=AccessLevel.USER, description="访问级别")

class KnowledgeItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="标题")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    source_type: Optional[SourceType] = Field(None, description="来源类型")
    knowledge_type: Optional[KnowledgeType] = Field(None, description="知识类型")
    sources: Optional[List[str]] = Field(None, description="来源列表")
    source_urls: Optional[List[str]] = Field(None, description="来源URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    subcategory: Optional[str] = Field(None, max_length=100, description="子分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    knowledge_bases: Optional[List[str]] = Field(None, description="知识库列表")
    access_level: Optional[AccessLevel] = Field(None, description="访问级别")

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    base_type: str = Field(default="general", max_length=50, description="类型")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    access_level: AccessLevel = Field(default=AccessLevel.USER, description="访问级别")
    collaborators: Optional[List[str]] = Field(None, description="协作者列表")

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    base_type: Optional[str] = Field(None, max_length=50, description="类型")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    access_level: Optional[AccessLevel] = Field(None, description="访问级别")
    collaborators: Optional[List[str]] = Field(None, description="协作者列表")
    is_active: Optional[bool] = Field(None, description="是否活跃")

class KnowledgeContentCreate(BaseModel):
    item_id: str = Field(..., description="条目ID")
    content_type: ContentType = Field(..., description="内容类型")
    content_text: Optional[str] = Field(None, max_length=16000, description="文本内容")
    content_ref: Optional[str] = Field(None, max_length=500, description="内容引用")
    content_size: int = Field(..., ge=0, description="内容大小")
    encoding: str = Field(default="utf-8", max_length=20, description="编码")
    checksum: Optional[str] = Field(None, max_length=64, description="校验和")
    parser_version: Optional[str] = Field(None, max_length=20, description="解析器版本")

class ResponseSchema(BaseModel):
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="消息")
    data: Optional[Any] = Field(None, description="数据")
    error_code: Optional[str] = Field(None, description="错误代码")

class PaginatedResponse(BaseModel):
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    items: List[Any] = Field(..., description="数据列表")

# 查询参数Schema
class KnowledgeItemQuery(BaseModel):
    title: Optional[str] = Field(None, description="标题搜索")
    source_type: Optional[SourceType] = Field(None, description="来源类型")
    knowledge_type: Optional[KnowledgeType] = Field(None, description="知识类型")
    status: Optional[ItemStatus] = Field(None, description="状态")
    tag: Optional[str] = Field(None, description="标签")
    created_by: Optional[str] = Field(None, description="创建者")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页大小")

class KnowledgeBaseQuery(BaseModel):
    name: Optional[str] = Field(None, description="名称搜索")
    category: Optional[str] = Field(None, description="分类")
    access_level: Optional[AccessLevel] = Field(None, description="访问级别")
    created_by: Optional[str] = Field(None, description="创建者")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页大小")