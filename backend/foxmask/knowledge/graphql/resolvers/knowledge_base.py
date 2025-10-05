# foxmask/knowledge/graphql/resolvers/knowledge_base_resolver.py
import strawberry
from typing import List, Optional
from strawberry.types import Info

from foxmask.core.schema import VisibilityEnum
from foxmask.knowledge.graphql.schemas.knowledge_base import (
    KnowledgeBaseType,
    KnowledgeBaseCreateInput,
    KnowledgeBaseUpdateInput,
    KnowledgeBaseList,
    MutationKnowledgeBaseResponse,
)
from foxmask.core.model import Status
from foxmask.knowledge.services import knowledge_base_service


@strawberry.type
class KnowledgeBaseQuery:
    """知识库查询Resolver"""
    
    @strawberry.field
    async def knowledge_base(
        self,
        info: Info,
        id: str
    ) -> Optional[KnowledgeBaseType]:
        """获取单个知识库"""
        tenant_id = info.context.get("tenant_id")
        if not tenant_id:
            return None
        
        knowledge_base = await knowledge_base_service.get_knowledge_base(id, tenant_id)
        if knowledge_base:
            # 检查用户权限
            user_id = info.context.get("user_id")
            user_roles = info.context.get("user_roles", [])
            if await knowledge_base_service.has_access(knowledge_base, user_id, user_roles):
                return KnowledgeBaseType.from_model(knowledge_base)
        return None
    
    @strawberry.field
    async def knowledge_bases(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None,
        category: Optional[str] = None
    ) -> KnowledgeBaseList:
        """列出知识库（管理员视图）"""
        tenant_id = info.context.get("tenant_id")
        if not tenant_id:
            return KnowledgeBaseList(items=[], total_count=0, has_more=False)
        
        items = await knowledge_base_service.list_knowledge_bases(
            tenant_id, skip, limit, status, category
        )
        total_count = await knowledge_base_service.count_knowledge_bases(tenant_id)
        
        return KnowledgeBaseList(
            items=[KnowledgeBaseType.from_model(item) for item in items],
            total_count=total_count,
            has_more=(skip + limit) < total_count
        )
    
    @strawberry.field
    async def my_knowledge_bases(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None
    ) -> KnowledgeBaseList:
        """列出用户有权限的知识库"""
        tenant_id = info.context.get("tenant_id")
        user_id = info.context.get("user_id")
        
        if not tenant_id or not user_id:
            return KnowledgeBaseList(items=[], total_count=0, has_more=False)
        
        items = await knowledge_base_service.list_user_knowledge_bases(
            tenant_id, user_id, skip, limit, status
        )
        total_count = len(items)
        
        return KnowledgeBaseList(
            items=[KnowledgeBaseType.from_model(item) for item in items],
            total_count=total_count,
            has_more=(skip + limit) < total_count
        )
    
    @strawberry.field
    async def search_knowledge_bases(
        self,
        info: Info,
        query: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None
    ) -> KnowledgeBaseList:
        """搜索知识库"""
        tenant_id = info.context.get("tenant_id")
        user_id = info.context.get("user_id")
        user_roles = info.context.get("user_roles", [])
        
        if not tenant_id:
            return KnowledgeBaseList(items=[], total_count=0, has_more=False)
        
        items = await knowledge_base_service.search_knowledge_bases(
            tenant_id, query, skip, limit, status
        )
        
        # 过滤用户有权限访问的结果
        accessible_items = []
        for item in items:
            if await knowledge_base_service.has_access(item, user_id, user_roles):
                accessible_items.append(item)
        
        return KnowledgeBaseList(
            items=[KnowledgeBaseType.from_model(item) for item in accessible_items],
            total_count=len(accessible_items),
            has_more=(skip + limit) < len(accessible_items)
        )


@strawberry.type
class KnowledgeBaseMutation:
    """知识库变更Resolver"""
    
    @strawberry.mutation
    async def create_knowledge_base(
        self,
        info: Info,
        input: KnowledgeBaseCreateInput
    ) -> MutationKnowledgeBaseResponse:
        """创建知识库"""
        tenant_id = info.context.get("tenant_id")
        user_id = info.context.get("user_id")
        
        if not tenant_id or not user_id:
            return MutationKnowledgeBaseResponse(
                success=False,
                message="未提供租户ID或用户ID"
            )
        
        try:
            knowledge_base = await knowledge_base_service.create_knowledge_base(
                title=input.title,
                description=input.description,
                tags=input.tags or [],
                category=input.category,
                tenant_id=tenant_id,
                created_by=user_id,
                visibility=input.visibility,
                allowed_users=input.allowed_users or [],
                allowed_roles=input.allowed_roles or [],
                metadata=input.metadata or {}
            )
            
            return MutationKnowledgeBaseResponse(
                success=True,
                message="知识库创建成功",
                data=KnowledgeBaseType.from_model(knowledge_base)
            )
        except Exception as e:
            return MutationKnowledgeBaseResponse(
                success=False,
                message=f"创建知识库失败: {str(e)}"
            )
    
    @strawberry.mutation
    async def update_knowledge_base(
        self,
        info: Info,
        id: str,
        input: KnowledgeBaseUpdateInput
    ) -> MutationKnowledgeBaseResponse:
        """更新知识库"""
        tenant_id = info.context.get("tenant_id")
        
        if not tenant_id:
            return MutationKnowledgeBaseResponse(
                success=False,
                message="未提供租户ID"
            )
        
        # 构建更新数据
        update_data = {}
        if input.title is not None:
            update_data['title'] = input.title
        if input.description is not None:
            update_data['description'] = input.description
        if input.tags is not None:
            update_data['tags'] = input.tags
        if input.category is not None:
            update_data['category'] = input.category
        if input.visibility is not None:
            update_data['visibility'] = input.visibility
        if input.allowed_users is not None:
            update_data['allowed_users'] = input.allowed_users
        if input.allowed_roles is not None:
            update_data['allowed_roles'] = input.allowed_roles
        if input.metadata is not None:
            update_data['metadata'] = input.metadata
        
        try:
            knowledge_base = await knowledge_base_service.update_knowledge_base(
                id, tenant_id, **update_data
            )
            
            if knowledge_base:
                return MutationKnowledgeBaseResponse(
                    success=True,
                    message="知识库更新成功",
                    data=KnowledgeBaseType.from_model(knowledge_base)
                )
            else:
                return MutationKnowledgeBaseResponse(
                    success=False,
                    message="知识库不存在或没有权限"
                )
        except Exception as e:
            return MutationKnowledgeBaseResponse(
                success=False,
                message=f"更新知识库失败: {str(e)}"
            )
    
    @strawberry.mutation
    async def delete_knowledge_base(
        self,
        info: Info,
        id: str
    ) -> MutationKnowledgeBaseResponse:
        """删除知识库"""
        tenant_id = info.context.get("tenant_id")
        
        if not tenant_id:
            return MutationKnowledgeBaseResponse(
                success=False,
                message="未提供租户ID"
            )
        
        try:
            success = await knowledge_base_service.delete_knowledge_base(id, tenant_id)
            
            if success:
                return MutationKnowledgeBaseResponse(
                    success=True,
                    message="知识库删除成功"
                )
            else:
                return MutationKnowledgeBaseResponse(
                    success=False,
                    message="知识库不存在或没有权限"
                )
        except Exception as e:
            return MutationKnowledgeBaseResponse(
                success=False,
                message=f"删除知识库失败: {str(e)}"
            )
    
    @strawberry.mutation
    async def change_knowledge_base_status(
        self,
        info: Info,
        id: str,
        status: Status
    ) -> MutationKnowledgeBaseResponse:
        """更改知识库状态"""
        tenant_id = info.context.get("tenant_id")
        
        if not tenant_id:
            return MutationKnowledgeBaseResponse(
                success=False,
                message="未提供租户ID"
            )
        
        try:
            knowledge_base = await knowledge_base_service.change_status(id, tenant_id, status)
            
            if knowledge_base:
                return MutationKnowledgeBaseResponse(
                    success=True,
                    message="状态更新成功",
                    data=KnowledgeBaseType.from_model(knowledge_base)
                )
            else:
                return MutationKnowledgeBaseResponse(
                    success=False,
                    message="知识库不存在或没有权限"
                )
        except Exception as e:
            return MutationKnowledgeBaseResponse(
                success=False,
                message=f"状态更新失败: {str(e)}"
            )
    
    