# -*- coding: utf-8 -*-
# foxmask/knowledge/services/knowledge_item_service.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from typing import List, Optional, Dict, Any

from foxmask.knowledge.models import (
    KnowledgeItem, 
    KnowledgeItemStatusEnum, 
    KnowledgeItemTypeEnum,
    KnowledgeItemContent,
    ItemContentTypeEnum
)
from foxmask.knowledge.repositories import (
    knowledge_item_repository,
    knowledge_item_content_repository
)
from foxmask.core.model import Visibility
from foxmask.utils.helpers import get_current_time


class KnowledgeItemService:
    """知识条目业务逻辑层"""
    
    def __init__(self):
        # 修正：直接使用导入的实例，不要再次调用
        self.item_repo = knowledge_item_repository
        self.content_repo = knowledge_item_content_repository
    
    async def create_knowledge_item(
        self,
        title: str,
        item_type: KnowledgeItemTypeEnum,
        tenant_id: str,
        created_by: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        visibility: Visibility = Visibility.PRIVATE,
        allowed_users: Optional[List[str]] = None,
        allowed_roles: Optional[List[str]] = None,
        content: Optional[Dict[str, Any]] = None
    ) -> KnowledgeItem:
        """创建知识条目"""
        item_data = {
            "title": title,
            "item_type": item_type,
            "tenant_id": tenant_id,
            "created_by": created_by,
            "description": description,
            "tags": tags or [],
            "category": category,
            "metadata": metadata or {},
            "visibility": visibility,
            "allowed_users": allowed_users or [],
            "allowed_roles": allowed_roles or [],
            "content": content or {},
            "status": KnowledgeItemStatusEnum.CREATED
        }
        
        return await self.item_repo.create_item(item_data)
    
    async def get_knowledge_item(self, item_id: str, tenant_id: str) -> Optional[KnowledgeItem]:
        """获取知识条目详情"""
        return await self.item_repo.get_item_by_id(item_id, tenant_id)
    
    async def update_knowledge_item(
        self,
        item_id: str,
        tenant_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[KnowledgeItem]:
        """更新知识条目"""
        # 验证用户权限（这里可以添加更复杂的权限验证逻辑）
        return await self.item_repo.update_item(item_id, tenant_id, update_data)
    
    async def delete_knowledge_item(self, item_id: str, tenant_id: str) -> bool:
        """删除知识条目"""
        # 先删除关联的内容
        await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.tenant_id == tenant_id
        ).delete()
        
        # 再删除条目
        return await self.item_repo.delete_item(item_id, tenant_id)
    
    async def list_knowledge_items(
        self,
        tenant_id: str,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[KnowledgeItemStatusEnum] = None,
        visibility: Optional[Visibility] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        search_text: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[KnowledgeItem]:
        """查询知识条目列表"""
        return await self.item_repo.list_items(
            tenant_id=tenant_id,
            item_type=item_type,
            status=status,
            visibility=visibility,
            created_by=created_by,
            tags=tags,
            category=category,
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def count_knowledge_items(
        self,
        tenant_id: str,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[KnowledgeItemStatusEnum] = None,
        visibility: Optional[Visibility] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> int:
        """统计知识条目数量"""
        return await self.item_repo.count_items(
            tenant_id=tenant_id,
            item_type=item_type,
            status=status,
            visibility=visibility,
            created_by=created_by,
            tags=tags,
            category=category,
            search_text=search_text
        )
    
    async def update_item_status(
        self,
        item_id: str,
        tenant_id: str,
        status: KnowledgeItemStatusEnum,
        processing_metadata: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> Optional[KnowledgeItem]:
        """更新知识条目状态"""
        return await self.item_repo.update_item_status(
            item_id, tenant_id, status, processing_metadata, error_info
        )
    
    async def add_content_to_item(
        self,
        item_id: str,
        content_type: ItemContentTypeEnum,
        content_data: Dict[str, Any],
        tenant_id: str,
        created_by: str,
        processing_metadata: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> KnowledgeItemContent:
        """为知识条目添加内容"""
        # 验证条目存在
        item = await self.get_knowledge_item(item_id, tenant_id)
        if not item:
            raise ValueError(f"Knowledge item {item_id} not found")
        
        content_data = {
            "item_id": item_id,
            "content_type": content_type,
            "content_data": content_data,
            "tenant_id": tenant_id,
            "created_by": created_by,
            "processing_metadata": processing_metadata or {},
            "error_info": error_info
        }
        
        return await self.content_repo.create_new_content_version(content_data, tenant_id)
    
    async def get_item_content(
        self,
        item_id: str,
        content_type: ItemContentTypeEnum,
        tenant_id: str,
        version: Optional[int] = None
    ) -> Optional[KnowledgeItemContent]:
        """获取知识条目内容"""
        if version:
            # 获取特定版本
            return await KnowledgeItemContent.find_one(
                KnowledgeItemContent.item_id == item_id,
                KnowledgeItemContent.content_type == content_type,
                KnowledgeItemContent.version == version,
                KnowledgeItemContent.tenant_id == tenant_id
            )
        else:
            # 获取最新版本
            return await self.content_repo.get_latest_content(item_id, content_type, tenant_id)
    
    async def get_item_content_versions(
        self,
        item_id: str,
        content_type: ItemContentTypeEnum,
        tenant_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> List[KnowledgeItemContent]:
        """获取内容的所有版本"""
        return await self.content_repo.get_content_versions(
            item_id, content_type, tenant_id, page, page_size
        )
    
    async def add_tag_to_item(self, item_id: str, tenant_id: str, tag: str) -> Optional[KnowledgeItem]:
        """为知识条目添加标签"""
        return await self.item_repo.add_tag_to_item(item_id, tenant_id, tag)
    
    async def remove_tag_from_item(self, item_id: str, tenant_id: str, tag: str) -> Optional[KnowledgeItem]:
        """从知识条目移除标签"""
        return await self.item_repo.remove_tag_from_item(item_id, tenant_id, tag)
    
    async def change_item_visibility(
        self,
        item_id: str,
        tenant_id: str,
        visibility: Visibility
    ) -> Optional[KnowledgeItem]:
        """更改知识条目可见性"""
        item = await self.get_knowledge_item(item_id, tenant_id)
        if not item:
            return None
        
        item.change_visibility(visibility)
        await item.save()
        return item
    
    async def check_item_access(
        self,
        item_id: str,
        tenant_id: str,
        user_id: str,
        user_roles: List[str]
    ) -> bool:
        """检查用户对知识条目的访问权限"""
        item = await self.get_knowledge_item(item_id, tenant_id)
        if not item:
            return False
        
        return item.has_access(user_id, user_roles)
    
    async def batch_get_items(self, item_ids: List[str], tenant_id: str) -> List[KnowledgeItem]:
        """批量获取知识条目"""
        return await self.item_repo.get_items_by_ids(item_ids, tenant_id)
    
    async def batch_update_items_status(
        self,
        item_ids: List[str],
        tenant_id: str,
        status: KnowledgeItemStatusEnum,
        processing_metadata: Optional[Dict[str, Any]] = None
    ) -> List[KnowledgeItem]:
        """批量更新知识条目状态"""
        updated_items = []
        for item_id in item_ids:
            item = await self.update_item_status(
                item_id, tenant_id, status, processing_metadata
            )
            if item:
                updated_items.append(item)
        return updated_items
    
# 创建服务实例
knowledge_item_service = KnowledgeItemService()