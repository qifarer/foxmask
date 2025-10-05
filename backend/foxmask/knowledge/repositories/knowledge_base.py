# 
# foxmask/knowledge/repositories/knowledge_base.py

from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from foxmask.knowledge.models import (
    KnowledgeBase, 
)    
from foxmask.core.model import Visibility,Status
from foxmask.utils.helpers import get_current_time


class KnowledgeBaseRepository:
    """知识库数据访问层"""
    
    async def create(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """创建知识库"""
        return await knowledge_base.insert()
    
    async def get_by_id(self, id: PydanticObjectId) -> Optional[KnowledgeBase]:
        """根据ID获取知识库"""
        return await KnowledgeBase.get(id)
    
    async def get_by_id_and_tenant(self, id: PydanticObjectId, tenant_id: str) -> Optional[KnowledgeBase]:
        """根据ID和租户ID获取知识库"""
        return await KnowledgeBase.find_one(KnowledgeBase.id == id, KnowledgeBase.tenant_id == tenant_id)
    
    async def list_by_tenant(
        self, 
        tenant_id: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[Status] = None,
        category: Optional[str] = None
    ) -> List[KnowledgeBase]:
        """根据租户ID列出知识库"""
        query = KnowledgeBase.tenant_id == tenant_id
        
        if status:
            query = query & (KnowledgeBase.status == status)
        
        if category:
            query = query & (KnowledgeBase.category == category)
        
        return await KnowledgeBase.find(
            query
        ).skip(skip).limit(limit).sort(-KnowledgeBase.created_at).to_list()
    
    async def list_by_user(
        self, 
        tenant_id: str, 
        user_id: str,
        skip: int = 0, 
        limit: int = 100,
        status: Optional[Status] = None
    ) -> List[KnowledgeBase]:
        """根据用户ID列出知识库"""
        query = (KnowledgeBase.tenant_id == tenant_id) & (
            (KnowledgeBase.created_by == user_id) |
            (KnowledgeBase.visibility == Visibility.PUBLIC) |
            (KnowledgeBase.visibility == Visibility.TENANT) |
            (KnowledgeBase.allowed_users.contains(user_id))
        )
        
        if status:
            query = query & (KnowledgeBase.status == status)
        
        return await KnowledgeBase.find(
            query
        ).skip(skip).limit(limit).sort(-KnowledgeBase.created_at).to_list()
    
    async def update(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        """更新知识库"""
        knowledge_base.updated_at = get_current_time()
        return await knowledge_base.save()
    
    async def delete(self, knowledge_base: KnowledgeBase) -> bool:
        """删除知识库"""
        return await knowledge_base.delete()
    
    async def delete_by_id(self, id: PydanticObjectId) -> bool:
        """根据ID删除知识库"""
        knowledge_base = await self.get_by_id(id)
        if knowledge_base:
            return await self.delete(knowledge_base)
        return False
    
    async def count_by_tenant(self, tenant_id: str) -> int:
        """统计租户的知识库数量"""
        return await KnowledgeBase.find(KnowledgeBase.tenant_id == tenant_id).count()
    
    async def search(
        self,
        tenant_id: str,
        query: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[Status] = None
    ) -> List[KnowledgeBase]:
        """搜索知识库"""
        search_query = {
            "tenant_id": tenant_id,
            "$text": {"$search": query}
        }
        
        if status:
            search_query["status"] = status
        
        return await KnowledgeBase.find(
            search_query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit).to_list()
    
    async def update_status(
        self, 
        id: PydanticObjectId, 
        status: Status
    ) -> Optional[KnowledgeBase]:
        """更新知识库状态"""
        knowledge_base = await self.get_by_id(id)
        if knowledge_base:
            knowledge_base.status = status
            knowledge_base.updated_at = get_current_time()
            return await knowledge_base.save()
        return None
    
    async def add_item(
        self, 
        id: PydanticObjectId, 
        item_key: str, 
        item_data: Dict[str, Any]
    ) -> Optional[KnowledgeBase]:
        """添加知识条目"""
        knowledge_base = await self.get_by_id(id)
        if knowledge_base:
            knowledge_base.items[item_key] = item_data
            knowledge_base.item_count = len(knowledge_base.items)
            knowledge_base.updated_at = get_current_time()
            return await knowledge_base.save()
        return None
    
    async def remove_item(self, id: PydanticObjectId, item_key: str) -> Optional[KnowledgeBase]:
        """移除知识条目"""
        knowledge_base = await self.get_by_id(id)
        if knowledge_base and item_key in knowledge_base.items:
            del knowledge_base.items[item_key]
            knowledge_base.item_count = len(knowledge_base.items)
            knowledge_base.updated_at = get_current_time()
            return await knowledge_base.save()
        return None
 
knowledge_base_repository = KnowledgeBaseRepository()   