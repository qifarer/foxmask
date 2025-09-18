# foxmask/knowledge/graphql/knowledge_item_resolver.py
import strawberry
from typing import List, Optional
from strawberry.types import Info


from .knowledge_item_schema import (
    KnowledgeItemFilter,
    KnowledgeItemType,
    PaginationInput,
    KnowledgeItemInput,
    KnowledgeItemUpdateInput,
    KnowledgeItemList,
    MutationKnowledgeItemResponse,
    BatchItemIdsInput,
)
from foxmask.core.model import Visibility

from .knowledge_content_schema import (
    KnowledgeItemContentType,
    KnowledgeItemContentList,
    KnowledgeItemContentInput,
)
from foxmask.knowledge.services import (
    knowledge_item_service,
    knowledge_base_service,
)
from foxmask.knowledge.models import KnowledgeItemContent,ItemContentTypeEnum,KnowledgeItemStatusEnum

# GraphQL 查询和变更
@strawberry.type
class KnowledgeItemQuery:
    @strawberry.field
    async def knowledge_item(
        self, 
        info: Info, 
        id: str
    ) -> Optional[KnowledgeItemType]:
        """获取单个知识条目"""
        # 从上下文中获取租户ID和用户信息
        context = info.context
        tenant_id = context.get("tenant_id")
        
        item = await knowledge_item_service.get_knowledge_item(id, tenant_id)
        if item:
            # 检查访问权限
            user_id = context.get("user_id")
            user_roles = context.get("user_roles", [])
            if await knowledge_item_service.check_item_access(id, tenant_id, user_id, user_roles):
                return KnowledgeItemType.from_model(item)
        return None
    
    @strawberry.field
    async def knowledge_items(
        self,
        info: Info,
        filter: Optional[KnowledgeItemFilter] = None,
        pagination: Optional[PaginationInput] = None
    ) -> KnowledgeItemList:
        """查询知识条目列表"""
        context = info.context
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")
        user_roles = context.get("user_roles", [])
        
        # 设置默认分页参数
        pagination = pagination or PaginationInput()
        filter = filter or KnowledgeItemFilter()
        
        # 获取列表
        items = await knowledge_item_service.list_knowledge_items(
            tenant_id=tenant_id,
            item_type=filter.item_type,
            status=filter.status,
            visibility=filter.visibility,
            created_by=filter.created_by,
            tags=filter.tags,
            category=filter.category,
            search_text=filter.search_text,
            page=pagination.page,
            page_size=pagination.page_size,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order
        )
        
        # 过滤用户有权限访问的条目
        accessible_items = []
        for item in items:
            if await knowledge_item_service.check_item_access(str(item.id), tenant_id, user_id, user_roles):
                accessible_items.append(KnowledgeItemType.from_model(item))
        
        # 获取总数
        total_count = await knowledge_item_service.count_knowledge_items(
            tenant_id=tenant_id,
            item_type=filter.item_type,
            status=filter.status,
            visibility=filter.visibility,
            created_by=filter.created_by,
            tags=filter.tags,
            category=filter.category,
            search_text=filter.search_text
        )
        
        has_next = (pagination.page * pagination.page_size) < total_count
        
        return KnowledgeItemList(
            items=accessible_items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=has_next
        )
    
    @strawberry.field
    async def knowledge_item_content(
        self,
        info: Info,
        item_id: str,
        content_type: ItemContentTypeEnum,
        version: Optional[int] = None
    ) -> Optional[KnowledgeItemContentType]:
        """获取知识条目内容"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        # 先检查条目访问权限
        user_id = context.get("user_id")
        user_roles = context.get("user_roles", [])
        if not await knowledge_item_service.check_item_access(item_id, tenant_id, user_id, user_roles):
            return None
        
        content = await knowledge_item_service.get_item_content(
            item_id, content_type.value, tenant_id, version
        )
        if content:
            return KnowledgeItemContentType.from_model(content)
        return None
    
    @strawberry.field
    async def knowledge_item_content_versions(
        self,
        info: Info,
        item_id: str,
        content_type: ItemContentTypeEnum,
        pagination: Optional[PaginationInput] = None
    ) -> KnowledgeItemContentList:
        """获取知识条目内容的所有版本"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        # 先检查条目访问权限
        user_id = context.get("user_id")
        user_roles = context.get("user_roles", [])
        if not await knowledge_item_service.check_item_access(item_id, tenant_id, user_id, user_roles):
            return KnowledgeItemContentList(items=[], total_count=0, page=1, page_size=20, has_next=False)
        
        pagination = pagination or PaginationInput()
        
        contents = await knowledge_item_service.get_item_content_versions(
            item_id, content_type.value, tenant_id, pagination.page, pagination.page_size
        )
        
        # 获取总版本数
        total_count = await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.content_type == content_type.value,
            KnowledgeItemContent.tenant_id == tenant_id
        ).count()
        
        has_next = (pagination.page * pagination.page_size) < total_count
        
        return KnowledgeItemContentList(
            items=[KnowledgeItemContentType.from_model(content) for content in contents],
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=has_next
        )
    
    @strawberry.field
    async def batch_knowledge_items(
        self,
        info: Info,
        input: BatchItemIdsInput
    ) -> List[KnowledgeItemType]:
        """批量获取知识条目"""
        context = info.context
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")
        user_roles = context.get("user_roles", [])
        
        items = await knowledge_item_service.batch_get_items(input.item_ids, tenant_id)
        
        # 过滤用户有权限访问的条目
        accessible_items = []
        for item in items:
            if await knowledge_item_service.check_item_access(str(item.id), tenant_id, user_id, user_roles):
                accessible_items.append(KnowledgeItemType.from_model(item))
        
        return accessible_items
    
    @strawberry.field
    async def knowledge_items_by_tag(
        self,
        info: Info,
        tag: str,
        pagination: Optional[PaginationInput] = None
    ) -> KnowledgeItemList:
        """根据标签查询知识条目"""
        context = info.context
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")
        user_roles = context.get("user_roles", [])
        
        pagination = pagination or PaginationInput()
        
        # 获取列表
        items = await knowledge_item_service.list_knowledge_items(
            tenant_id=tenant_id,
            tags=[tag],
            page=pagination.page,
            page_size=pagination.page_size,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order
        )
        
        # 过滤用户有权限访问的条目
        accessible_items = []
        for item in items:
            if await knowledge_item_service.check_item_access(str(item.id), tenant_id, user_id, user_roles):
                accessible_items.append(KnowledgeItemType.from_model(item))
        
        # 获取总数
        total_count = await knowledge_item_service.count_knowledge_items(
            tenant_id=tenant_id,
            tags=[tag]
        )
        
        has_next = (pagination.page * pagination.page_size) < total_count
        
        return KnowledgeItemList(
            items=accessible_items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=has_next
        )


@strawberry.type
class KnowledgeItemMutation:
    @strawberry.mutation
    async def create_knowledge_item(
        self,
        info: Info,
        input: KnowledgeItemInput
    ) -> MutationKnowledgeItemResponse:
        """创建知识条目"""
        context = info.context
        tenant_id = context.get("tenant_id")
        created_by = context.get("user_id")
        
        try:
            item = await knowledge_item_service.create_knowledge_item(
                title=input.title,
                item_type=input.item_type,
                tenant_id=tenant_id,
                created_by=created_by,
                description=input.description,
                tags=input.tags,
                category=input.category,
                metadata=input.metadata,
                visibility=input.visibility,
                allowed_users=input.allowed_users,
                allowed_roles=input.allowed_roles,
                content=input.content
            )
            
            return MutationKnowledgeItemResponse(
                success=True,
                message="Knowledge item created successfully",
                item=KnowledgeItemType.from_model(item)
            )
        except Exception as e:
            return MutationKnowledgeItemResponse(
                success=False,
                message=f"Failed to create knowledge item: {str(e)}"
            )
    
    @strawberry.mutation
    async def update_knowledge_item(
        self,
        info: Info,
        id: str,
        input: KnowledgeItemUpdateInput
    ) -> MutationKnowledgeItemResponse:
        """更新知识条目"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        # 转换为字典并移除None值
        update_data = {k: v for k, v in input.__dict__.items() if v is not None}
        
        try:
            item = await knowledge_item_service.update_knowledge_item(id, tenant_id, update_data)
            if item:
                return MutationKnowledgeItemResponse(
                    success=True,
                    message="Knowledge item updated successfully",
                    item=KnowledgeItemType.from_model(item)
                )
            else:
                return MutationKnowledgeItemResponse(
                    success=False,
                    message="Knowledge item not found"
                )
        except Exception as e:
            return MutationKnowledgeItemResponse(
                success=False,
                message=f"Failed to update knowledge item: {str(e)}"
            )
    
    @strawberry.mutation
    async def delete_knowledge_item(
        self,
        info: Info,
        id: str
    ) -> MutationKnowledgeItemResponse:
        """删除知识条目"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        success = await knowledge_item_service.delete_knowledge_item(id, tenant_id)
        if success:
            return MutationKnowledgeItemResponse(
                success=True,
                message="Knowledge item deleted successfully"
            )
        else:
            return MutationKnowledgeItemResponse(
                success=False,
                message="Knowledge item not found or failed to delete"
            )
    
    @strawberry.mutation
    async def add_content_to_knowledge_item(
        self,
        info: Info,
        item_id: str,
        input: KnowledgeItemContentInput
    ) -> MutationKnowledgeItemResponse:
        """为知识条目添加内容"""
        context = info.context
        tenant_id = context.get("tenant_id")
        created_by = context.get("user_id")
        
        try:
            content = await knowledge_item_service.add_content_to_item(
                item_id=item_id,
                content_type=input.content_type,
                content_data=input.content_data,
                tenant_id=tenant_id,
                created_by=created_by,
                processing_metadata=input.processing_metadata
            )
            
            return MutationKnowledgeItemResponse(
                success=True,
                message="Content added to knowledge item successfully",
                content=KnowledgeItemContentType.from_model(content)
            )
        except Exception as e:
            return MutationKnowledgeItemResponse(
                success=False,
                message=f"Failed to add content: {str(e)}"
            )
    
    @strawberry.mutation
    async def add_tag_to_knowledge_item(
        self,
        info: Info,
        item_id: str,
        tag: str
    ) -> MutationKnowledgeItemResponse:
        """为知识条目添加标签"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        item = await knowledge_item_service.add_tag_to_item(item_id, tenant_id, tag)
        if item:
            return MutationKnowledgeItemResponse(
                success=True,
                message="Tag added successfully",
                item=KnowledgeItemType.from_model(item)
            )
        else:
            return MutationKnowledgeItemResponse(
                success=False,
                message="Knowledge item not found"
            )
    
    @strawberry.mutation
    async def remove_tag_from_knowledge_item(
        self,
        info: Info,
        item_id: str,
        tag: str
    ) -> MutationKnowledgeItemResponse:
        """从知识条目移除标签"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        item = await knowledge_item_service.remove_tag_from_item(item_id, tenant_id, tag)
        if item:
            return MutationKnowledgeItemResponse(
                success=True,
                message="Tag removed successfully",
                item=KnowledgeItemType.from_model(item)
            )
        else:
            return MutationKnowledgeItemResponse(
                success=False,
                message="Knowledge item not found"
            )
    
    @strawberry.mutation
    async def change_knowledge_item_visibility(
        self,
        info: Info,
        item_id: str,
        visibility: Visibility
    ) -> MutationKnowledgeItemResponse:
        """更改知识条目可见性"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        item = await knowledge_item_service.change_item_visibility(item_id, tenant_id, visibility)
        if item:
            return MutationKnowledgeItemResponse(
                success=True,
                message="Visibility changed successfully",
                item=KnowledgeItemType.from_model(item)
            )
        else:
            return MutationKnowledgeItemResponse(
                success=False,
                message="Knowledge item not found"
            )
    
    @strawberry.mutation
    async def update_knowledge_item_status(
        self,
        info: Info,
        item_id: str,
        status: KnowledgeItemStatusEnum,
        processing_metadata: Optional[strawberry.scalars.JSON] = None,
        error_info: Optional[strawberry.scalars.JSON] = None
    ) -> MutationKnowledgeItemResponse:
        """更新知识条目状态"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        item = await knowledge_item_service.update_item_status(
            item_id, tenant_id, status, processing_metadata, error_info
        )
        if item:
            return MutationKnowledgeItemResponse(
                success=True,
                message="Status updated successfully",
                item=KnowledgeItemType.from_model(item)
            )
        else:
            return MutationKnowledgeItemResponse(
                success=False,
                message="Knowledge item not found"
            )
    
    @strawberry.mutation
    async def batch_update_knowledge_items_status(
        self,
        info: Info,
        input: BatchItemIdsInput,
        status: KnowledgeItemStatusEnum,
        processing_metadata: Optional[strawberry.scalars.JSON] = None
    ) -> List[KnowledgeItemType]:
        """批量更新知识条目状态"""
        context = info.context
        tenant_id = context.get("tenant_id")
        
        items = await knowledge_item_service.batch_update_items_status(
            input.item_ids, tenant_id, status, processing_metadata
        )
        
        return [KnowledgeItemType.from_model(item) for item in items]