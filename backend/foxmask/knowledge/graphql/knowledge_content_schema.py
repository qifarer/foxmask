# foxmask/knowledge/graphql/knowledge_content_schema.py
import strawberry
from typing import Optional,List
from strawberry.scalars import JSON
from foxmask.knowledge.models import ItemContentTypeEnum

@strawberry.type
class KnowledgeItemContentType:
    """知识内容GraphQL类型"""
    id: strawberry.ID
    item_id: str
    content_type: ItemContentTypeEnum
    content_data: JSON
    processing_metadata: JSON
    error_info: Optional[JSON]
    version: int
    is_latest: bool
    tenant_id: str
    created_at: str
    updated_at: str
    created_by: str

    @classmethod
    def from_model(cls, model):
        """从Pydantic模型转换"""
        return cls(
            id=str(model.id),
            item_id=model.item_id,
            content_type=model.content_type,
            content_data=model.content_data,
            processing_metadata=model.processing_metadata,
            error_info=model.error_info,
            version=model.version,
            is_latest=model.is_latest,
            tenant_id=model.tenant_id,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
            created_by=model.created_by
        )


@strawberry.input
class KnowledgeItemContentInput:
    """知识内容输入"""
    content_type: ItemContentTypeEnum
    content_data: JSON
    processing_metadata: Optional[JSON] = None


@strawberry.input
class KnowledgeContentFilter:
    """知识内容筛选条件"""
    content_type: Optional[ItemContentTypeEnum] = None
    is_latest: Optional[bool] = None


@strawberry.type
class KnowledgeItemContentList:
    """知识内容列表"""
    items: List[KnowledgeItemContentType]
    total_count: int
    page: int
    page_size: int
    has_next: bool


@strawberry.type
class MutationKnowledgeContentResponse:
    """知识内容变更操作响应"""
    success: bool
    message: Optional[str] = None
    content: Optional[KnowledgeItemContentType] = None