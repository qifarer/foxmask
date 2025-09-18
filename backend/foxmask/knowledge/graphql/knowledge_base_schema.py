# foxmask/knowledge/schemas/knowledge_base_schema.py
import strawberry
from typing import List, Optional
from beanie import PydanticObjectId
from strawberry.scalars import JSON

from foxmask.knowledge.models import KnowledgeBaseStatusEnum
from foxmask.core.schema import VisibilityEnum
from enum import Enum

@strawberry.type
class KnowledgeBaseType:
    """知识库GraphQL类型"""
    id: strawberry.ID
    title: str
    description: Optional[str]
    tags: List[str]
    category: Optional[str]
    metadata: JSON
    tenant_id: str
    visibility: VisibilityEnum
    allowed_users: List[str]
    allowed_roles: List[str]
    created_at: str
    updated_at: str
    created_by: str
    items: JSON
    item_count: int
    status: KnowledgeBaseStatusEnum
    
    @classmethod
    def from_model(cls, model):
        """从Pydantic模型转换"""
        return cls(
            id=str(model.id),
            title=model.title,
            description=model.description,
            tags=model.tags,
            category=model.category,
            metadata=model.metadata,
            tenant_id=model.tenant_id,
            visibility=model.visibility,
            allowed_users=model.allowed_users,
            allowed_roles=model.allowed_roles,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
            created_by=model.created_by,
            items=model.items,
            item_count=model.item_count,
            status=model.status
        )


@strawberry.input
class KnowledgeBaseCreateInput:
    """创建知识库输入"""
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    visibility: Optional[VisibilityEnum] = VisibilityEnum.PRIVATE
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None


@strawberry.input
class KnowledgeBaseUpdateInput:
    """更新知识库输入"""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    visibility: Optional[VisibilityEnum] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None

@strawberry.input
class KnowledgeBaseFilter:
    """知识库筛选条件"""
    status: Optional[KnowledgeBaseStatusEnum] = None
    category: Optional[str] = None
    search_text: Optional[str] = None
    visibility: Optional[VisibilityEnum] = None


@strawberry.input
class PaginationInput:
    """分页输入"""
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


@strawberry.type
class KnowledgeBaseList:
    """知识库列表"""
    items: List[KnowledgeBaseType]
    total_count: int
    page: int
    page_size: int
    has_next: bool


@strawberry.type
class MutationKnowledgeBaseResponse:
    """知识库变更操作响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[KnowledgeBaseType] = None