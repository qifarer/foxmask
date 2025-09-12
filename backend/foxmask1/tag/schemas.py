from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import TagTypeEnum
from uuid import UUID

class TagSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    # 核心标识
    id: str = Field(..., description="MongoDB ID")
    tag_id: UUID = Field(..., description="标签业务ID")
    name: str = Field(..., max_length=50, description="标签名称")
    slug: str = Field(..., max_length=50, description="标签slug")
    
    # 分类信息
    tag_type: TagTypeEnum = Field(..., description="标签类型")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    
    # 多语言支持
    display_name: Dict[str, str] = Field(default_factory=dict, description="多语言显示名称")
    description: Dict[str, str] = Field(default_factory=dict, description="多语言描述")
    
    # 样式配置
    color: str = Field(..., max_length=7, description="颜色")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    background_color: Optional[str] = Field(None, max_length=7, description="背景颜色")
    text_color: Optional[str] = Field(None, max_length=7, description="文字颜色")
    
    # 层级关系
    parent_id: Optional[str] = Field(None, description="父标签ID")
    path: List[str] = Field(default_factory=list, description="标签路径")
    depth: int = Field(default=0, description="层级深度")
    children_count: int = Field(default=0, description="子标签数量")
    
    # 权限控制
    is_public: bool = Field(..., description="是否公开")
    visibility: str = Field(..., description="可见性级别")
    status: str = Field(..., description="标签状态")
    tagging_permission: str = Field(..., description="标记权限")
    
    # 归属信息
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    owner_id: str = Field(..., max_length=50, description="所有者ID")
    team_id: Optional[str] = Field(None, max_length=50, description="团队ID")
    created_by: str = Field(..., max_length=50, description="创建者ID")
    updated_by: str = Field(..., max_length=50, description="更新者ID")
    
    # 统计信息
    usage_count: int = Field(..., description="使用次数")
    popularity_score: float = Field(..., description="流行度分数")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    trend_score: float = Field(..., description="趋势分数")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    synonyms: List[str] = Field(default_factory=list, description="同义词")
    related_tags: List[str] = Field(default_factory=list, description="相关标签")
    
    # 验证规则
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    max_usage_limit: Optional[int] = Field(None, description="最大使用限制")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    approved_at: Optional[datetime] = Field(None, description="审核通过时间")
    
    # 软删除状态
    is_deleted: bool = Field(..., description="是否删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")

class TaggedObjectSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: str = Field(..., description="标记关系ID")
    tag_id: str = Field(..., description="标签ID")
    object_type: str = Field(..., max_length=50, description="对象类型")
    object_id: str = Field(..., description="对象ID")
    
    # 标记信息
    tagged_by: str = Field(..., max_length=50, description="标记者ID")
    tagged_at: datetime = Field(..., description="标记时间")
    weight: float = Field(..., description="权重")
    weight_level: str = Field(..., description="权重级别")
    
    # 上下文信息
    context: Optional[Dict[str, Any]] = Field(None, description="标记上下文")
    confidence: float = Field(..., description="置信度")
    source: str = Field(..., max_length=50, description="来源")
    
    # 有效期
    valid_from: Optional[datetime] = Field(None, description="生效时间")
    valid_until: Optional[datetime] = Field(None, description="失效时间")
    is_active: bool = Field(..., description="是否活跃")
    
    # 审核信息
    reviewed_by: Optional[str] = Field(None, max_length=50, description="审核者")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    review_status: str = Field(..., max_length=20, description="审核状态")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class TagUsageStatsSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: str = Field(..., description="统计ID")
    tag_id: str = Field(..., description="标签ID")
    tag_name: str = Field(..., description="标签名称")
    object_type: str = Field(..., description="对象类型")
    period: str = Field(..., description="统计周期")
    period_date: datetime = Field(..., description="统计日期")
    
    # 使用统计
    usage_count: int = Field(..., description="使用次数")
    unique_objects: int = Field(..., description="唯一对象数")
    unique_users: int = Field(..., description="唯一用户数")
    
    # 权重统计
    total_weight: float = Field(..., description="总权重")
    average_weight: float = Field(..., description="平均权重")
    
    # 趋势指标
    trend_score: float = Field(..., description="趋势分数")
    growth_rate: float = Field(..., description="增长率")
    
    # 时间戳
    calculated_at: datetime = Field(..., description="计算时间")

class TagCollectionSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    id: str = Field(..., description="集合ID")
    collection_id: UUID = Field(..., description="集合业务ID")
    name: str = Field(..., max_length=100, description="集合名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    
    # 集合配置
    tags: List[str] = Field(default_factory=list, description="标签列表")
    collection_type: str = Field(..., max_length=20, description="集合类型")
    is_public: bool = Field(..., description="是否公开")
    
    # 权限控制
    owner_id: str = Field(..., max_length=50, description="所有者ID")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    collaborators: List[str] = Field(default_factory=list, description="协作者")
    
    # 统计信息
    tag_count: int = Field(..., description="标签数量")
    usage_count: int = Field(..., description="使用次数")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    tag_type: TagTypeEnum = Field(default=TagTypeEnum.USER, description="标签类型")
    description: Optional[Dict[str, str]] = Field(None, description="多语言描述")
    color: Optional[str] = Field(None, max_length=7, description="颜色")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    parent_id: Optional[str] = Field(None, description="父标签ID")
    is_public: bool = Field(default=True, description="是否公开")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="标签名称")
    description: Optional[Dict[str, str]] = Field(None, description="多语言描述")
    color: Optional[str] = Field(None, max_length=7, description="颜色")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    parent_id: Optional[str] = Field(None, description="父标签ID")
    is_public: Optional[bool] = Field(None, description="是否公开")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    status: Optional[str] = Field(None, description="标签状态")

class TaggedObjectCreate(BaseModel):
    tag_id: str = Field(..., description="标签ID")
    object_type: str = Field(..., max_length=50, description="对象类型")
    object_id: str = Field(..., description="对象ID")
    weight: Optional[float] = Field(1.0, ge=0.0, le=10.0, description="权重")
    context: Optional[Dict[str, Any]] = Field(None, description="标记上下文")
    source: Optional[str] = Field("manual", max_length=50, description="来源")

class TagCollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="集合名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    collection_type: Optional[str] = Field("manual", max_length=20, description="集合类型")
    is_public: Optional[bool] = Field(True, description="是否公开")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    collaborators: Optional[List[str]] = Field(None, description="协作者")

class TagQuery(BaseModel):
    tag_type: Optional[TagTypeEnum] = Field(None, description="标签类型")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    is_public: Optional[bool] = Field(None, description="是否公开")
    created_by: Optional[str] = Field(None, description="创建者")
    parent_id: Optional[str] = Field(None, description="父标签ID")
    status: Optional[str] = Field(None, description="标签状态")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页大小")

class TagSearchQuery(BaseModel):
    query: str = Field(..., description="搜索查询")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页大小")

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