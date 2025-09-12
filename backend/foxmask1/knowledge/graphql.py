import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import KnowledgeType, SourceType, ItemStatus, AccessLevel, ContentType
from .services import knowledge_item_service, knowledge_base_service
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

@strawberry.type
class KnowledgeItemType:
    id: strawberry.ID
    title: str
    description: Optional[str]
    summary: Optional[str]
    source_type: SourceType
    knowledge_type: KnowledgeType
    category: Optional[str]
    subcategory: Optional[str]
    sources: List[str]
    source_urls: List[str]
    original_format: Optional[str]
    metadata: strawberry.scalars.JSON
    language: str
    version: int
    content_refs: strawberry.scalars.JSON
    status: ItemStatus
    processing_steps: List[strawberry.scalars.JSON]
    error_message: Optional[str]
    retry_count: int
    access_level: AccessLevel
    tenant_id: Optional[str]
    created_by: str
    updated_by: str
    tag_refs: List[strawberry.ID]
    knowledge_bases: List[strawberry.ID]
    related_items: List[strawberry.ID]
    vector_id: Optional[str]
    graph_id: Optional[str]
    embedding_model: Optional[str]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]

@strawberry.type
class KnowledgeBaseType:
    id: strawberry.ID
    name: str
    description: Optional[str]
    cover_image: Optional[str]
    category: Optional[str]
    base_type: str
    access_level: AccessLevel
    tenant_id: Optional[str]
    created_by: str
    collaborators: List[str]
    item_count: int
    total_size: int
    items: List[strawberry.ID]
    tag_refs: List[strawberry.ID]
    parent_base: Optional[strawberry.ID]
    child_bases: List[strawberry.ID]
    settings: strawberry.scalars.JSON
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]

@strawberry.type
class KnowledgeContentType:
    id: strawberry.ID
    item_id: strawberry.ID
    content_type: ContentType
    content_text: Optional[str]
    content_ref: Optional[str]
    content_size: int
    encoding: str
    checksum: Optional[str]
    parser_version: Optional[str]
    extracted_entities: List[strawberry.scalars.JSON]
    extracted_keywords: List[str]
    access_level: AccessLevel
    tenant_id: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

@strawberry.input
class KnowledgeItemInput:
    title: str
    description: Optional[str] = None
    summary: Optional[str] = None
    source_type: SourceType
    knowledge_type: KnowledgeType
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sources: Optional[List[str]] = None
    source_urls: Optional[List[str]] = None
    original_format: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    language: Optional[str] = "zh-CN"
    tags: Optional[List[str]] = None
    knowledge_bases: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    access_level: Optional[AccessLevel] = AccessLevel.USER

@strawberry.input
class KnowledgeItemUpdateInput:
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    source_type: Optional[SourceType] = None
    knowledge_type: Optional[KnowledgeType] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sources: Optional[List[str]] = None
    source_urls: Optional[List[str]] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None
    knowledge_bases: Optional[List[str]] = None
    access_level: Optional[AccessLevel] = None

@strawberry.input
class KnowledgeBaseInput:
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    base_type: Optional[str] = "general"
    tags: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    access_level: Optional[AccessLevel] = AccessLevel.USER
    collaborators: Optional[List[str]] = None

@strawberry.input
class KnowledgeBaseUpdateInput:
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    base_type: Optional[str] = None
    tags: Optional[List[str]] = None
    access_level: Optional[AccessLevel] = None
    collaborators: Optional[List[str]] = None
    is_active: Optional[bool] = None

@strawberry.input
class KnowledgeContentInput:
    item_id: str
    content_type: ContentType
    content_text: Optional[str] = None
    content_ref: Optional[str] = None
    content_size: int
    encoding: Optional[str] = "utf-8"
    checksum: Optional[str] = None
    parser_version: Optional[str] = None

@strawberry.type
class PaginationInfo:
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool

@strawberry.type
class KnowledgeItemConnection:
    items: List[KnowledgeItemType]
    pagination: PaginationInfo

@strawberry.type
class KnowledgeBaseConnection:
    bases: List[KnowledgeBaseType]
    pagination: PaginationInfo

@strawberry.type
class MutationResult:
    success: bool
    message: Optional[str] = None
    id: Optional[strawberry.ID] = None

@strawberry.type
class Query:
    @strawberry.field
    async def knowledge_items(
        self, 
        skip: int = 0, 
        limit: int = 10,
        title: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        status: Optional[ItemStatus] = None,
        created_by: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> KnowledgeItemConnection:
        """获取知识条目列表（支持过滤和分页）"""
        try:
            filters = {}
            if title:
                filters["title"] = title
            if source_type:
                filters["source_type"] = source_type
            if knowledge_type:
                filters["knowledge_type"] = knowledge_type
            if status:
                filters["status"] = status
            if created_by:
                filters["created_by"] = created_by
            if tenant_id:
                filters["tenant_id"] = tenant_id
            
            items = await knowledge_item_service.list_items(skip, limit, filters)
            
            # 简化处理，实际应该从数据库获取总数
            total = len(items)
            has_next = total > skip + limit
            has_prev = skip > 0
            
            return KnowledgeItemConnection(
                items=[_convert_item_to_type(item) for item in items],
                pagination=PaginationInfo(
                    total=total,
                    page=skip // limit + 1,
                    size=limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch knowledge items: {e}")
            return KnowledgeItemConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

    @strawberry.field
    async def knowledge_item(
        self, 
        id: strawberry.ID
    ) -> Optional[KnowledgeItemType]:
        """根据ID获取知识条目"""
        try:
            if not ObjectId.is_valid(id):
                return None
                
            item = await knowledge_item_service.get_item(ObjectId(id))
            if not item:
                return None
                
            return _convert_item_to_type(item)
            
        except Exception as e:
            logger.error(f"Failed to fetch knowledge item {id}: {e}")
            return None

    @strawberry.field
    async def knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 10,
        name: Optional[str] = None,
        category: Optional[str] = None,
        access_level: Optional[AccessLevel] = None,
        created_by: Optional[str] = None,
        tenant_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> KnowledgeBaseConnection:
        """获取知识库列表（支持过滤和分页）"""
        try:
            filters = {}
            if name:
                filters["name"] = name
            if category:
                filters["category"] = category
            if access_level:
                filters["access_level"] = access_level
            if created_by:
                filters["created_by"] = created_by
            if tenant_id:
                filters["tenant_id"] = tenant_id
            if is_active is not None:
                filters["is_active"] = is_active
            
            bases = await knowledge_base_service.list_bases(skip, limit, filters)
            
            # 简化处理
            total = len(bases)
            has_next = total > skip + limit
            has_prev = skip > 0
            
            return KnowledgeBaseConnection(
                bases=[_convert_base_to_type(base) for base in bases],
                pagination=PaginationInfo(
                    total=total,
                    page=skip // limit + 1,
                    size=limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch knowledge bases: {e}")
            return KnowledgeBaseConnection(bases=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

    @strawberry.field
    async def knowledge_base(
        self, 
        id: strawberry.ID
    ) -> Optional[KnowledgeBaseType]:
        """根据ID获取知识库"""
        try:
            if not ObjectId.is_valid(id):
                return None
                
            base = await knowledge_base_service.get_base(ObjectId(id))
            if not base:
                return None
                
            return _convert_base_to_type(base)
            
        except Exception as e:
            logger.error(f"Failed to fetch knowledge base {id}: {e}")
            return None

    @strawberry.field
    async def search_knowledge_items(
        self,
        query: str,
        skip: int = 0,
        limit: int = 10
    ) -> KnowledgeItemConnection:
        """搜索知识条目"""
        try:
            items = await knowledge_item_service.search_items(query, skip, limit)
            
            # 简化处理
            total = len(items)
            has_next = total > skip + limit
            has_prev = skip > 0
            
            return KnowledgeItemConnection(
                items=[_convert_item_to_type(item) for item in items],
                pagination=PaginationInfo(
                    total=total,
                    page=skip // limit + 1,
                    size=limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to search knowledge items: {e}")
            return KnowledgeItemConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_knowledge_item(
        self, 
        input: KnowledgeItemInput
    ) -> MutationResult:
        """创建知识条目"""
        try:
            # 转换知识库ID格式
            knowledge_base_ids = []
            if input.knowledge_bases:
                knowledge_base_ids = [
                    ObjectId(kb_id) for kb_id in input.knowledge_bases 
                    if ObjectId.is_valid(kb_id)
                ]
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            item = await knowledge_item_service.create_item(
                title=input.title,
                description=input.description,
                source_type=input.source_type,
                knowledge_type=input.knowledge_type,
                sources=input.sources or [],
                source_urls=input.source_urls or [],
                metadata=input.metadata or {},
                user_id=user_id,
                updated_by=user_id,
                tenant_id=input.tenant_id,
                tags=input.tags,
                knowledge_bases=knowledge_base_ids,
                category=input.category,
                subcategory=input.subcategory
            )
            
            return MutationResult(
                success=True,
                message="Knowledge item created successfully",
                id=str(item.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to create knowledge item: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def update_knowledge_item(
        self, 
        id: strawberry.ID,
        input: KnowledgeItemUpdateInput
    ) -> MutationResult:
        """更新知识条目"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid ID format")
            
            # 转换知识库ID格式
            knowledge_base_ids = None
            if input.knowledge_bases is not None:
                knowledge_base_ids = [
                    ObjectId(kb_id) for kb_id in input.knowledge_bases 
                    if ObjectId.is_valid(kb_id)
                ]
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            item = await knowledge_item_service.update_item(
                ObjectId(id),
                title=input.title,
                description=input.description,
                source_type=input.source_type,
                knowledge_type=input.knowledge_type,
                sources=input.sources,
                source_urls=input.source_urls,
                metadata=input.metadata,
                updated_by=user_id,
                tags=input.tags,
                knowledge_bases=knowledge_base_ids,
                category=input.category,
                subcategory=input.subcategory,
                access_level=input.access_level
            )
            
            if not item:
                return MutationResult(success=False, message="Item not found")
            
            return MutationResult(
                success=True,
                message="Knowledge item updated successfully",
                id=str(item.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to update knowledge item {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def delete_knowledge_item(
        self, 
        id: strawberry.ID
    ) -> MutationResult:
        """删除知识条目"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid ID format")
            
            success = await knowledge_item_service.delete_item(ObjectId(id))
            
            if not success:
                return MutationResult(success=False, message="Item not found")
            
            return MutationResult(
                success=True,
                message="Knowledge item deleted successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge item {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def create_knowledge_base(
        self, 
        input: KnowledgeBaseInput
    ) -> MutationResult:
        """创建知识库"""
        try:
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            base = await knowledge_base_service.create_base(
                name=input.name,
                description=input.description,
                user_id=user_id,
                tenant_id=input.tenant_id,
                access_level=input.access_level,
                tags=input.tags,
                category=input.category,
                collaborators=input.collaborators or []
            )
            
            return MutationResult(
                success=True,
                message="Knowledge base created successfully",
                id=str(base.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def update_knowledge_base(
        self, 
        id: strawberry.ID,
        input: KnowledgeBaseUpdateInput
    ) -> MutationResult:
        """更新知识库"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid ID format")
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            base = await knowledge_base_service.update_base(
                ObjectId(id),
                name=input.name,
                description=input.description,
                updated_by=user_id,
                tags=input.tags,
                category=input.category,
                access_level=input.access_level,
                collaborators=input.collaborators,
                is_active=input.is_active
            )
            
            if not base:
                return MutationResult(success=False, message="Base not found")
            
            return MutationResult(
                success=True,
                message="Knowledge base updated successfully",
                id=str(base.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to update knowledge base {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def delete_knowledge_base(
        self, 
        id: strawberry.ID
    ) -> MutationResult:
        """删除知识库"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid ID format")
            
            success = await knowledge_base_service.delete_base(ObjectId(id))
            
            if not success:
                return MutationResult(success=False, message="Base not found")
            
            return MutationResult(
                success=True,
                message="Knowledge base deleted successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge base {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def add_item_to_base(
        self,
        base_id: strawberry.ID,
        item_id: strawberry.ID
    ) -> MutationResult:
        """将知识条目添加到知识库"""
        try:
            if not ObjectId.is_valid(base_id) or not ObjectId.is_valid(item_id):
                return MutationResult(success=False, message="Invalid ID format")
            
            success = await knowledge_base_service.add_item_to_base(
                ObjectId(base_id), ObjectId(item_id)
            )
            
            if not success:
                return MutationResult(success=False, message="Base or item not found")
            
            return MutationResult(
                success=True,
                message="Item added to base successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to add item to base: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def remove_item_from_base(
        self,
        base_id: strawberry.ID,
        item_id: strawberry.ID
    ) -> MutationResult:
        """从知识库移除知识条目"""
        try:
            if not ObjectId.is_valid(base_id) or not ObjectId.is_valid(item_id):
                return MutationResult(success=False, message="Invalid ID format")
            
            success = await knowledge_base_service.remove_item_from_base(
                ObjectId(base_id), ObjectId(item_id)
            )
            
            if not success:
                return MutationResult(success=False, message="Base or item not found")
            
            return MutationResult(
                success=True,
                message="Item removed from base successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to remove item from base: {e}")
            return MutationResult(success=False, message=str(e))

# 辅助函数
def _convert_item_to_type(item) -> KnowledgeItemType:
    """将KnowledgeItem转换为GraphQL类型"""
    return KnowledgeItemType(
        id=str(item.id),
        title=item.title,
        description=item.description,
        summary=item.summary,
        source_type=item.source_type,
        knowledge_type=item.knowledge_type,
        category=item.category,
        subcategory=item.subcategory,
        sources=item.sources,
        source_urls=item.source_urls,
        original_format=item.original_format,
        metadata=item.metadata,
        language=item.language,
        version=item.version,
        content_refs=item.content_refs,
        status=item.status,
        processing_steps=item.processing_steps,
        error_message=item.error_message,
        retry_count=item.retry_count,
        access_level=item.access_level,
        tenant_id=item.tenant_id,
        created_by=item.created_by,
        updated_by=item.updated_by,
        tag_refs=[str(tag.id) for tag in item.tag_refs] if hasattr(item, 'tag_refs') else [],
        knowledge_bases=[str(kb.id) for kb in item.knowledge_bases] if hasattr(item, 'knowledge_bases') else [],
        related_items=[str(ri.id) for ri in item.related_items] if hasattr(item, 'related_items') else [],
        vector_id=item.vector_id,
        graph_id=item.graph_id,
        embedding_model=item.embedding_model,
        created_at=item.created_at,
        updated_at=item.updated_at,
        processed_at=item.processed_at,
        is_deleted=item.is_deleted,
        deleted_at=item.deleted_at
    )

def _convert_base_to_type(base) -> KnowledgeBaseType:
    """将KnowledgeBase转换为GraphQL类型"""
    return KnowledgeBaseType(
        id=str(base.id),
        name=base.name,
        description=base.description,
        cover_image=base.cover_image,
        category=base.category,
        base_type=base.base_type,
        access_level=base.access_level,
        tenant_id=base.tenant_id,
        created_by=base.created_by,
        collaborators=base.collaborators,
        item_count=base.item_count,
        total_size=base.total_size,
        items=[str(item.id) for item in base.items] if hasattr(base, 'items') else [],
        tag_refs=[str(tag.id) for tag in base.tag_refs] if hasattr(base, 'tag_refs') else [],
        parent_base=str(base.parent_base.id) if base.parent_base else None,
        child_bases=[str(cb.id) for cb in base.child_bases] if hasattr(base, 'child_bases') else [],
        settings=base.settings,
        is_active=base.is_active,
        created_at=base.created_at,
        updated_at=base.updated_at,
        last_activity=base.last_activity,
        is_deleted=base.is_deleted,
        deleted_at=base.deleted_at
    )

schema = strawberry.Schema(query=Query, mutation=Mutation)    
graphql_app = GraphQLRouter(schema)