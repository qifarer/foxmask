import strawberry
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import TagTypeEnum as TagTypeModel
from .services import tag_service
from bson import ObjectId
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

@strawberry.type
class TagType:
    id: strawberry.ID
    tag_id: strawberry.ID
    name: str
    slug: str
    tag_type: TagTypeModel
    category: Optional[str]
    display_name: strawberry.scalars.JSON
    description: strawberry.scalars.JSON
    color: str
    icon: Optional[str]
    background_color: Optional[str]
    text_color: Optional[str]
    parent_id: Optional[strawberry.ID]
    path: List[strawberry.ID]
    depth: int
    children_count: int
    is_public: bool
    visibility: str
    status: str
    tagging_permission: str
    tenant_id: Optional[str]
    owner_id: str
    team_id: Optional[str]
    created_by: str
    updated_by: str
    usage_count: int
    popularity_score: float
    last_used_at: Optional[datetime]
    trend_score: float
    metadata: strawberry.scalars.JSON
    synonyms: List[str]
    related_tags: List[strawberry.ID]
    validation_rules: Optional[strawberry.scalars.JSON]
    max_usage_limit: Optional[int]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]

@strawberry.type
class TaggedObjectType:
    id: strawberry.ID
    tag_id: strawberry.ID
    object_type: str
    object_id: strawberry.ID
    tagged_by: str
    tagged_at: datetime
    weight: float
    weight_level: str
    context: Optional[strawberry.scalars.JSON]
    confidence: float
    source: str
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    is_active: bool
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_status: str
    metadata: strawberry.scalars.JSON

@strawberry.type
class TagUsageStatsType:
    id: strawberry.ID
    tag_id: strawberry.ID
    tag_name: str
    object_type: str
    period: str
    period_date: datetime
    usage_count: int
    unique_objects: int
    unique_users: int
    total_weight: float
    average_weight: float
    trend_score: float
    growth_rate: float
    calculated_at: datetime

@strawberry.type
class TagCollectionType:
    id: strawberry.ID
    collection_id: strawberry.ID
    name: str
    description: Optional[str]
    tags: List[strawberry.ID]
    collection_type: str
    is_public: bool
    owner_id: str
    tenant_id: Optional[str]
    collaborators: List[str]
    tag_count: int
    usage_count: int
    created_at: datetime
    updated_at: datetime

@strawberry.input
class TagInput:
    name: str
    tag_type: Optional[TagTypeModel] = TagTypeModel.USER
    description: Optional[strawberry.scalars.JSON] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[strawberry.ID] = None
    is_public: Optional[bool] = True
    tenant_id: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class TagUpdateInput:
    name: Optional[str] = None
    description: Optional[strawberry.scalars.JSON] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[strawberry.ID] = None
    is_public: Optional[bool] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    status: Optional[str] = None

@strawberry.input
class TaggedObjectInput:
    tag_id: strawberry.ID
    object_type: str
    object_id: strawberry.ID
    weight: Optional[float] = 1.0
    context: Optional[strawberry.scalars.JSON] = None
    source: Optional[str] = "manual"

@strawberry.input
class TagQueryInput:
    tag_type: Optional[TagTypeModel] = None
    tenant_id: Optional[str] = None
    is_public: Optional[bool] = None
    created_by: Optional[str] = None
    parent_id: Optional[strawberry.ID] = None
    status: Optional[str] = None
    skip: int = 0
    limit: int = 10

@strawberry.type
class PaginationInfo:
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool

@strawberry.type
class TagConnection:
    items: List[TagType]
    pagination: PaginationInfo

@strawberry.type
class TaggedObjectConnection:
    items: List[TaggedObjectType]
    pagination: PaginationInfo

@strawberry.type
class MutationResult:
    success: bool
    message: Optional[str] = None
    id: Optional[strawberry.ID] = None

@strawberry.type
class Query:
    @strawberry.field
    async def tags(self, query: Optional[TagQueryInput] = None) -> TagConnection:
        """获取标签列表（支持过滤和分页）"""
        try:
            if query is None:
                query = TagQueryInput()
            
            # 构建过滤条件
            filters = {}
            if query.tag_type:
                filters["tag_type"] = query.tag_type
            if query.tenant_id:
                filters["tenant_id"] = query.tenant_id
            if query.is_public is not None:
                filters["is_public"] = query.is_public
            if query.created_by:
                filters["created_by"] = query.created_by
            if query.parent_id and ObjectId.is_valid(query.parent_id):
                filters["parent_id"] = ObjectId(query.parent_id)
            if query.status:
                filters["status"] = query.status
            
            tags = await tag_service.list_tags(
                skip=query.skip,
                limit=query.limit,
                filters=filters
            )
            
            # 简化处理
            total = len(tags)
            has_next = total > query.skip + query.limit
            has_prev = query.skip > 0
            
            return TagConnection(
                items=[_convert_tag_to_type(tag) for tag in tags],
                pagination=PaginationInfo(
                    total=total,
                    page=query.skip // query.limit + 1,
                    size=query.limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch tags: {e}")
            return TagConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

    @strawberry.field
    async def tag(self, id: strawberry.ID) -> Optional[TagType]:
        """根据ID获取标签"""
        try:
            if not ObjectId.is_valid(id):
                return None
                
            tag = await tag_service.get_tag(ObjectId(id))
            if not tag:
                return None
                
            return _convert_tag_to_type(tag)
            
        except Exception as e:
            logger.error(f"Failed to fetch tag {id}: {e}")
            return None

    @strawberry.field
    async def tag_by_name(self, name: str, tenant_id: Optional[str] = None) -> Optional[TagType]:
        """根据名称获取标签"""
        try:
            tag = await tag_service.get_tag_by_name(name, tenant_id)
            if not tag:
                return None
                
            return _convert_tag_to_type(tag)
            
        except Exception as e:
            logger.error(f"Failed to fetch tag by name {name}: {e}")
            return None

    @strawberry.field
    async def tag_by_slug(self, slug: str, tenant_id: Optional[str] = None) -> Optional[TagType]:
        """根据slug获取标签"""
        try:
            tag = await tag_service.get_tag_by_slug(slug, tenant_id)
            if not tag:
                return None
                
            return _convert_tag_to_type(tag)
            
        except Exception as e:
            logger.error(f"Failed to fetch tag by slug {slug}: {e}")
            return None

    @strawberry.field
    async def search_tags(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> TagConnection:
        """搜索标签"""
        try:
            tags = await tag_service.search_tags(query, skip, limit, tenant_id)
            
            # 简化处理
            total = len(tags)
            has_next = total > skip + limit
            has_prev = skip > 0
            
            return TagConnection(
                items=[_convert_tag_to_type(tag) for tag in tags],
                pagination=PaginationInfo(
                    total=total,
                    page=skip // limit + 1,
                    size=limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to search tags: {e}")
            return TagConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

    @strawberry.field
    async def popular_tags(
        self, 
        limit: int = 10,
        tenant_id: Optional[str] = None
    ) -> List[TagType]:
        """获取热门标签"""
        try:
            tags = await tag_service.get_popular_tags(limit, tenant_id)
            return [_convert_tag_to_type(tag) for tag in tags]
            
        except Exception as e:
            logger.error(f"Failed to fetch popular tags: {e}")
            return []

    @strawberry.field
    async def object_tags(
        self,
        object_type: str,
        object_id: strawberry.ID,
        active_only: bool = True
    ) -> List[TagType]:
        """获取对象的标签"""
        try:
            if not ObjectId.is_valid(object_id):
                return []
                
            tags = await tag_service.get_object_tags(object_type, ObjectId(object_id), active_only)
            return [_convert_tag_to_type(tag) for tag in tags]
            
        except Exception as e:
            logger.error(f"Failed to fetch object tags: {e}")
            return []

    @strawberry.field
    async def tagged_objects(
        self,
        tag_id: strawberry.ID,
        object_type: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 10
    ) -> TaggedObjectConnection:
        """获取标签标记的对象"""
        try:
            if not ObjectId.is_valid(tag_id):
                return TaggedObjectConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))
                
            objects = await tag_service.get_tagged_objects(
                ObjectId(tag_id), object_type, active_only, skip, limit
            )
            
            # 简化处理
            total = len(objects)
            has_next = total > skip + limit
            has_prev = skip > 0
            
            return TaggedObjectConnection(
                items=[_convert_tagged_object_to_type(obj) for obj in objects],
                pagination=PaginationInfo(
                    total=total,
                    page=skip // limit + 1,
                    size=limit,
                    has_next=has_next,
                    has_prev=has_prev
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch tagged objects: {e}")
            return TaggedObjectConnection(items=[], pagination=PaginationInfo(total=0, page=0, size=0, has_next=False, has_prev=False))

    @strawberry.field
    async def related_tags(
        self,
        tag_id: strawberry.ID,
        limit: int = 10
    ) -> List[TagType]:
        """获取相关标签"""
        try:
            if not ObjectId.is_valid(tag_id):
                return []
                
            tags = await tag_service.get_related_tags(ObjectId(tag_id), limit)
            return [_convert_tag_to_type(tag) for tag in tags]
            
        except Exception as e:
            logger.error(f"Failed to fetch related tags: {e}")
            return []

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_tag(self, input: TagInput) -> MutationResult:
        """创建标签"""
        try:
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            # 检查标签名是否已存在
            existing_tag = await tag_service.get_tag_by_name(input.name, input.tenant_id)
            if existing_tag:
                return MutationResult(success=False, message="Tag with this name already exists")
            
            # 转换父标签ID
            parent_id = None
            if input.parent_id and ObjectId.is_valid(input.parent_id):
                parent_id = ObjectId(input.parent_id)
            
            tag = await tag_service.create_tag(
                name=input.name,
                user_id=user_id,
                tag_type=input.tag_type or TagTypeModel.USER,
                description=input.description,
                color=input.color,
                icon=input.icon,
                parent_id=parent_id,
                is_public=input.is_public or True,
                tenant_id=input.tenant_id,
                metadata=input.metadata
            )
            
            return MutationResult(
                success=True,
                message="Tag created successfully",
                id=str(tag.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to create tag: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def update_tag(
        self,
        id: strawberry.ID,
        input: TagUpdateInput
    ) -> MutationResult:
        """更新标签"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid tag ID format")
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            tag = await tag_service.update_tag(
                ObjectId(id),
                user_id=user_id,
                name=input.name,
                description=input.description,
                color=input.color,
                icon=input.icon,
                parent_id=ObjectId(input.parent_id) if input.parent_id and ObjectId.is_valid(input.parent_id) else None,
                is_public=input.is_public,
                metadata=input.metadata,
                status=input.status
            )
            
            if not tag:
                return MutationResult(success=False, message="Tag not found")
            
            return MutationResult(
                success=True,
                message="Tag updated successfully",
                id=str(tag.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to update tag {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def delete_tag(self, id: strawberry.ID) -> MutationResult:
        """删除标签"""
        try:
            if not ObjectId.is_valid(id):
                return MutationResult(success=False, message="Invalid tag ID format")
            
            success = await tag_service.delete_tag(ObjectId(id))
            
            if not success:
                return MutationResult(success=False, message="Tag not found")
            
            return MutationResult(
                success=True,
                message="Tag deleted successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete tag {id}: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def tag_object(self, input: TaggedObjectInput) -> MutationResult:
        """标记对象"""
        try:
            if not ObjectId.is_valid(input.tag_id) or not ObjectId.is_valid(input.object_id):
                return MutationResult(success=False, message="Invalid ID format")
            
            # 验证对象类型
            valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
            if input.object_type not in valid_types:
                return MutationResult(success=False, message="Invalid object type")
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            tagged_object = await tag_service.tag_object(
                ObjectId(input.tag_id),
                input.object_type,
                ObjectId(input.object_id),
                user_id,
                input.weight or 1.0,
                input.context,
                input.source or "manual"
            )
            
            if not tagged_object:
                return MutationResult(success=False, message="Failed to tag object")
            
            return MutationResult(
                success=True,
                message="Object tagged successfully",
                id=str(tagged_object.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to tag object: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def untag_object(self, input: TaggedObjectInput) -> MutationResult:
        """取消标记对象"""
        try:
            if not ObjectId.is_valid(input.tag_id) or not ObjectId.is_valid(input.object_id):
                return MutationResult(success=False, message="Invalid ID format")
            
            # 验证对象类型
            valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
            if input.object_type not in valid_types:
                return MutationResult(success=False, message="Invalid object type")
            
            success = await tag_service.untag_object(
                ObjectId(input.tag_id),
                input.object_type,
                ObjectId(input.object_id)
            )
            
            if not success:
                return MutationResult(success=False, message="Tag relationship not found")
            
            return MutationResult(
                success=True,
                message="Object untagged successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to untag object: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def batch_tag_objects(
        self,
        tag_names: List[str],
        object_type: str,
        object_id: strawberry.ID
    ) -> MutationResult:
        """批量标记对象"""
        try:
            if not ObjectId.is_valid(object_id):
                return MutationResult(success=False, message="Invalid object ID format")
            
            # 验证对象类型
            valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
            if object_type not in valid_types:
                return MutationResult(success=False, message="Invalid object type")
            
            # 在实际应用中，这里需要获取当前用户ID
            user_id = "system_user"
            
            tagged_ids = await tag_service.batch_tag_objects(
                tag_names,
                object_type,
                ObjectId(object_id),
                user_id
            )
            
            return MutationResult(
                success=True,
                message=f"Successfully tagged {len(tagged_ids)} objects",
                data={"tagged_ids": [str(tid) for tid in tagged_ids]}
            )
            
        except Exception as e:
            logger.error(f"Failed to batch tag objects: {e}")
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def batch_untag_objects(
        self,
        tag_names: List[str],
        object_type: str,
        object_id: strawberry.ID
    ) -> MutationResult:
        """批量取消标记对象"""
        try:
            if not ObjectId.is_valid(object_id):
                return MutationResult(success=False, message="Invalid object ID format")
            
            # 验证对象类型
            valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
            if object_type not in valid_types:
                return MutationResult(success=False, message="Invalid object type")
            
            success = await tag_service.batch_untag_objects(
                tag_names,
                object_type,
                ObjectId(object_id)
            )
            
            return MutationResult(
                success=success,
                message="Objects untagged successfully" if success else "Failed to untag objects"
            )
            
        except Exception as e:
            logger.error(f"Failed to batch untag objects: {e}")
            return MutationResult(success=False, message=str(e))

# 辅助函数
def _convert_tag_to_type(tag) -> TagType:
    """将Tag转换为GraphQL类型"""
    return TagType(
        id=str(tag.id),
        tag_id=str(tag.tag_id),
        name=tag.name,
        slug=tag.slug,
        tag_type=tag.tag_type,
        category=tag.category,
        display_name=tag.display_name,
        description=tag.description,
        color=tag.color,
        icon=tag.icon,
        background_color=tag.background_color,
        text_color=tag.text_color,
        parent_id=str(tag.parent_id) if tag.parent_id else None,
        path=[str(p) for p in tag.path],
        depth=tag.depth,
        children_count=tag.children_count,
        is_public=tag.is_public,
        visibility=tag.visibility,
        status=tag.status,
        tagging_permission=tag.tagging_permission,
        tenant_id=tag.tenant_id,
        owner_id=tag.owner_id,
        team_id=tag.team_id,
        created_by=tag.created_by,
        updated_by=tag.updated_by,
        usage_count=tag.usage_count,
        popularity_score=tag.popularity_score,
        last_used_at=tag.last_used_at,
        trend_score=tag.trend_score,
        metadata=tag.metadata,
        synonyms=tag.synonyms,
        related_tags=[str(rt) for rt in tag.related_tags],
        validation_rules=tag.validation_rules,
        max_usage_limit=tag.max_usage_limit,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        approved_at=tag.approved_at,
        is_deleted=tag.is_deleted,
        deleted_at=tag.deleted_at
    )

def _convert_tagged_object_to_type(tagged_object) -> TaggedObjectType:
    """将TaggedObject转换为GraphQL类型"""
    return TaggedObjectType(
        id=str(tagged_object.id),
        tag_id=str(tagged_object.tag_id),
        object_type=tagged_object.object_type,
        object_id=str(tagged_object.object_id),
        tagged_by=tagged_object.tagged_by,
        tagged_at=tagged_object.tagged_at,
        weight=tagged_object.weight,
        weight_level=tagged_object.weight_level,
        context=tagged_object.context,
        confidence=tagged_object.confidence,
        source=tagged_object.source,
        valid_from=tagged_object.valid_from,
        valid_until=tagged_object.valid_until,
        is_active=tagged_object.is_active,
        reviewed_by=tagged_object.reviewed_by,
        reviewed_at=tagged_object.reviewed_at,
        review_status=tagged_object.review_status,
        metadata=tagged_object.metadata
    )

# 创建schema和GraphQL路由
from strawberry.fastapi import GraphQLRouter

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)