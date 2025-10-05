# foxmask/knowledge/services/knowledge_base.py
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from foxmask.knowledge.models import (
    KnowledgeBase, 
)
from foxmask.knowledge.repositories import knowledge_base_repository
from foxmask.core.model import Visibility,Status
from foxmask.utils.helpers import get_current_time

class KnowledgeBaseService:
    """知识库业务逻辑层"""
    
    def __init__(self):
        self.repository = knowledge_base_repository
    
    async def create_knowledge_base(
        self,
        title: str,
        tenant_id: str,
        created_by: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        visibility: Visibility = Visibility.PRIVATE,
        allowed_users: Optional[List[str]] = None,
        allowed_roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBase:
        """创建知识库"""
        knowledge_base = KnowledgeBase(
            title=title,
            description=description,
            tags=tags or [],
            category=category,
            tenant_id=tenant_id,
            created_by=created_by,
            visibility=visibility,
            allowed_users=allowed_users or [],
            allowed_roles=allowed_roles or [],
            metadata=metadata or {},
            items={},
            item_count=0,
            status=Status.DRAFT
        )
        
        return await self.repository.create(knowledge_base)
    
    async def get_knowledge_base(
        self, 
        id: PydanticObjectId, 
        tenant_id: str
    ) -> Optional[KnowledgeBase]:
        """获取知识库"""
        return await self.repository.get_by_id_and_tenant(id, tenant_id)
    
    async def list_knowledge_bases(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None,
        category: Optional[str] = None
    ) -> List[KnowledgeBase]:
        """列出知识库"""
        return await self.repository.list_by_tenant(
            tenant_id, skip, limit, status, category
        )
    
    async def list_user_knowledge_bases(
        self,
        tenant_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None
    ) -> List[KnowledgeBase]:
        """列出用户有权限访问的知识库"""
        return await self.repository.list_by_user(
            tenant_id, user_id, skip, limit, status
        )
    
    async def update_knowledge_base(
        self,
        id: PydanticObjectId,
        tenant_id: str,
        **update_data
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        knowledge_base = await self.repository.get_by_id_and_tenant(id, tenant_id)
        if not knowledge_base:
            return None
        
        # 过滤允许更新的字段
        allowed_fields = {
            'title', 'description', 'tags', 'category', 'metadata',
            'visibility', 'allowed_users', 'allowed_roles'
        }
        
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(knowledge_base, field):
                setattr(knowledge_base, field, value)
        
        return await self.repository.update(knowledge_base)
    
    async def delete_knowledge_base(
        self, 
        id: PydanticObjectId, 
        tenant_id: str
    ) -> bool:
        """删除知识库"""
        knowledge_base = await self.repository.get_by_id_and_tenant(id, tenant_id)
        if knowledge_base:
            return await self.repository.delete(knowledge_base)
        return False
    
    async def change_status(
        self,
        id: PydanticObjectId,
        tenant_id: str,
        status: Status
    ) -> Optional[KnowledgeBase]:
        """更改知识库状态"""
        knowledge_base = await self.repository.get_by_id_and_tenant(id, tenant_id)
        if knowledge_base:
            return await self.repository.update_status(id, status)
        return None
    
    async def add_knowledge_item(
        self,
        id: PydanticObjectId,
        tenant_id: str,
        item_key: str,
        item_data: Dict[str, Any]
    ) -> Optional[KnowledgeBase]:
        """添加知识条目"""
        knowledge_base = await self.repository.get_by_id_and_tenant(id, tenant_id)
        if knowledge_base:
            return await self.repository.add_item(id, item_key, item_data)
        return None
    
    async def remove_knowledge_item(
        self,
        id: PydanticObjectId,
        tenant_id: str,
        item_key: str
    ) -> Optional[KnowledgeBase]:
        """移除知识条目"""
        knowledge_base = await self.repository.get_by_id_and_tenant(id, tenant_id)
        if knowledge_base:
            return await self.repository.remove_item(id, item_key)
        return None
    
    async def search_knowledge_bases(
        self,
        tenant_id: str,
        query: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None
    ) -> List[KnowledgeBase]:
        """搜索知识库"""
        return await self.repository.search(tenant_id, query, skip, limit, status)
    
    async def count_knowledge_bases(self, tenant_id: str) -> int:
        """统计知识库数量"""
        return await self.repository.count_by_tenant(tenant_id)
    
    async def has_access(
        self,
        knowledge_base: KnowledgeBase,
        user_id: str,
        user_roles: List[str]
    ) -> bool:
        """检查用户是否有访问权限"""
        return knowledge_base.has_access(user_id, user_roles)
    
knowledge_base_service = KnowledgeBaseService()