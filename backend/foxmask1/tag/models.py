from enum import Enum
from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field, validator, ConfigDict
from typing import Optional, List, Set, Dict, Any
from bson import ObjectId
from uuid import UUID, uuid4

class TagTypeEnum(str, Enum):
    """标签类型枚举"""
    SYSTEM = "system"        # 系统标签
    USER = "user"            # 用户自定义标签
    CATEGORY = "category"    # 分类标签
    TOPIC = "topic"          # 主题标签
    STATUS = "status"        # 状态标签

class Tag(Document):
    """标签核心实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )
    
    # MongoDB ObjectId作为主键
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    
    # 业务标识
    tag_id: UUID = Field(default_factory=uuid4, unique=True, description="标签业务ID")
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    slug: str = Field(..., min_length=1, max_length=50, description="标签slug")
    
    # 分类信息
    tag_type: TagTypeEnum = Field(default=TagTypeEnum.USER, description="标签类型")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    
    # 多语言支持
    display_name: Dict[str, str] = Field(default_factory=dict, description="多语言显示名称")
    description: Dict[str, str] = Field(default_factory=dict, description="多语言描述")
    
    # 样式配置
    color: str = Field(
        default="#C05E3B",
        max_length=7,
        pattern=r"^#[0-9A-Fa-f]{6}$",  # ✅ 用 pattern 替代 regex
        description="颜色"
    )
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    background_color: Optional[str] = Field(None, max_length=7, description="背景颜色")
    text_color: Optional[str] = Field(None, max_length=7, description="文字颜色")
    
    # 层级关系
    parent_id: Optional[ObjectId] = Field(None, description="父标签ID")
    path: List[ObjectId] = Field(default_factory=list, description="标签路径")
    depth: int = Field(default=0, ge=0, description="层级深度")
    children_count: int = Field(default=0, ge=0, description="子标签数量")
    
    # 权限控制
    is_public: bool = Field(default=True, description="是否公开")
    visibility: str = Field(default="public", description="可见性级别")
    status: str = Field(default="active", description="标签状态")
    tagging_permission: str = Field(default="members", description="标记权限")
    
    # 归属信息
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    owner_id: str = Field(..., max_length=50, description="所有者ID")
    team_id: Optional[str] = Field(None, max_length=50, description="团队ID")
    created_by: str = Field(..., max_length=50, description="创建者ID")
    updated_by: str = Field(..., max_length=50, description="更新者ID")
    
    # 统计信息
    usage_count: int = Field(default=0, ge=0, description="使用次数")
    popularity_score: float = Field(default=0.0, ge=0.0, description="流行度分数")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    trend_score: float = Field(default=0.0, description="趋势分数")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    synonyms: List[str] = Field(default_factory=list, description="同义词")
    related_tags: List[ObjectId] = Field(default_factory=list, description="相关标签")
    
    # 验证规则
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    max_usage_limit: Optional[int] = Field(None, ge=0, description="最大使用限制")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = Field(None, description="审核通过时间")
    
    # 软删除支持
    is_deleted: bool = Field(default=False, description="是否删除")
    deleted_at: Optional[datetime] = Field(None, description="删除时间")
    
    class Settings:
        name = "tags"
        indexes = [
            # 核心索引
            "tag_id",
            "name",
            "slug",
            "tag_type",
            "is_public",
            "status",
            "tenant_id",
            "owner_id",
            "created_by",
            "created_at",
            "is_deleted",
            
            # 复合索引
            [("tenant_id", 1), ("name", 1)],  # 租户内标签名唯一
            [("tag_type", 1), ("is_public", 1)],
            [("parent_id", 1), ("status", 1)],
            [("usage_count", -1), ("popularity_score", -1)],
            [("created_at", -1), ("trend_score", -1)],
            
            # 文本索引
            [("name", "text"), ("description", "text")],
            
            # 唯一约束
            [("tenant_id", 1), ("slug", 1), ("unique", True)],
            [("tenant_id", 1), ("name", 1), ("unique", True)],
            
            # TTL索引，用于自动清理软删除的标签（30天后）
            [("is_deleted", 1), ("deleted_at", 1), ("expireAfterSeconds", 2592000)]
        ]
    
    @validator('name')
    def validate_name(cls, v):
        """标签名称验证"""
        v = v.strip()
        if not v:
            raise ValueError("标签名称不能为空")
        if len(v) > 50:
            raise ValueError("标签名称不能超过50个字符")
        return v
    
    @validator('slug')
    def validate_slug(cls, v):
        """验证slug格式"""
        import re
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError('Slug只能包含小写字母、数字和连字符')
        return v
    
    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_usage(self, weight: float = 1.0):
        """增加使用计数"""
        self.usage_count += 1
        self.popularity_score += weight
        self.last_used_at = datetime.now(timezone.utc)
        self.update_timestamp()
    
    def add_synonym(self, synonym: str):
        """添加同义词"""
        if synonym and synonym not in self.synonyms:
            self.synonyms.append(synonym)
            self.update_timestamp()
    
    def approve(self, approved_by: str):
        """审核通过"""
        self.status = "active"
        self.approved_at = datetime.now(timezone.utc)
        self.updated_by = approved_by
        self.update_timestamp()
    
    def mark_as_deleted(self):
        """标记为软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.update_timestamp()

class TaggedObject(Document):
    """标记关系实体"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )
    
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    
    # 标记关系
    tag_id: ObjectId = Field(..., description="标签ID")
    object_type: str = Field(..., max_length=50, description="对象类型")
    object_id: ObjectId = Field(..., description="对象ID")
    
    # 标记信息
    tagged_by: str = Field(..., max_length=50, description="标记者ID")
    tagged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    weight: float = Field(default=1.0, ge=0.0, le=10.0, description="权重")
    weight_level: str = Field(default="medium", description="权重级别")
    
    # 上下文信息
    context: Optional[Dict[str, Any]] = Field(None, description="标记上下文")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    source: str = Field(default="manual", max_length=50, description="来源")
    
    # 有效期
    valid_from: Optional[datetime] = Field(None, description="生效时间")
    valid_until: Optional[datetime] = Field(None, description="失效时间")
    is_active: bool = Field(default=True, description="是否活跃")
    
    # 审核信息
    reviewed_by: Optional[str] = Field(None, max_length=50, description="审核者")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    review_status: str = Field(default="approved", max_length=20, description="审核状态")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    class Settings:
        name = "tagged_objects"
        indexes = [
            # 核心索引
            "tag_id",
            "object_type", 
            "object_id",
            "tagged_by",
            "tagged_at",
            "is_active",
            "review_status",
            
            # 复合索引
            [("object_type", 1), ("object_id", 1), ("tag_id", 1)],  # 唯一性约束
            [("tag_id", 1), ("object_type", 1), ("is_active", 1)],
            [("tagged_by", 1), ("tagged_at", -1)],  # 按用户和时间排序
            [("object_id", 1), ("object_type", 1), ("weight", -1)],  # 按权重排序
            [("review_status", 1), ("reviewed_at", 1)],
            
            # TTL索引，用于自动过期
            [("valid_until", 1), ("expireAfterSeconds", 0)]  # 到期自动删除
        ]
    
    @validator('object_type')
    def validate_object_type(cls, v):
        """验证对象类型"""
        valid_types = {
            'knowledge_item', 'knowledge_base', 'file', 'user', 
            'document', 'asset', 'project', 'task', 'comment'
        }
        if v not in valid_types:
            raise ValueError(f"无效的对象类型: {v}")
        return v

class TagUsageStats(Document):
    """标签使用统计"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )
    
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    
    # 统计维度
    tag_id: ObjectId = Field(..., description="标签ID")
    tag_name: str = Field(..., description="标签名称")
    object_type: str = Field(..., description="对象类型")
    period: str = Field(..., description="统计周期")  # daily, weekly, monthly
    period_date: datetime = Field(..., description="统计日期")
    
    # 使用统计
    usage_count: int = Field(default=0, ge=0, description="使用次数")
    unique_objects: int = Field(default=0, ge=0, description="唯一对象数")
    unique_users: int = Field(default=0, ge=0, description="唯一用户数")
    
    # 权重统计
    total_weight: float = Field(default=0.0, ge=0.0, description="总权重")
    average_weight: float = Field(default=0.0, ge=0.0, description="平均权重")
    
    # 趋势指标
    trend_score: float = Field(default=0.0, description="趋势分数")
    growth_rate: float = Field(default=0.0, description="增长率")
    
    # 时间戳
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "tag_usage_stats"
        indexes = [
            [("tag_id", 1), ("period", 1), ("period_date", 1)],  # 复合主键
            [("period_date", -1), ("trend_score", -1)],
            [("usage_count", -1)],
            [("object_type", 1), ("usage_count", -1)],
        ]

class TagCollection(Document):
    """标签集合"""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )
    
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    collection_id: UUID = Field(default_factory=uuid4, unique=True)
    name: str = Field(..., max_length=100, description="集合名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    
    # 集合配置
    tags: List[ObjectId] = Field(default_factory=list, description="标签列表")
    collection_type: str = Field(default="manual", max_length=20, description="集合类型")
    is_public: bool = Field(default=True, description="是否公开")
    
    # 权限控制
    owner_id: str = Field(..., max_length=50, description="所有者ID")
    tenant_id: Optional[str] = Field(None, max_length=50, description="租户ID")
    collaborators: List[str] = Field(default_factory=list, description="协作者")
    
    # 统计信息
    tag_count: int = Field(default=0, ge=0, description="标签数量")
    usage_count: int = Field(default=0, ge=0, description="使用次数")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "tag_collections"
        indexes = [
            "collection_id",
            "name",
            "owner_id",
            "tenant_id",
            "is_public",
            "created_at",
        ]