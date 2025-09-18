# -*- coding: utf-8 -*-
# foxmask/knowledge/services/knowledge_item_service.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from datetime import datetime

from foxmask.knowledge.models import (
    KnowledgeItem,
    KnowledgeItemStatusEnum,
    KnowledgeItemTypeEnum,
    KnowledgeItemContent,
    ItemContentTypeEnum
)
from foxmask.knowledge.repositories.knowledge_item_1 import KnowledgeItemRepository
from foxmask.core.model import Visibility
from foxmask.utils.helpers import get_current_time

@dataclass
class KnowledgeItemInput:
    title: str
    item_type: KnowledgeItemTypeEnum
    tenant_id: str
    created_by: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    visibility: Visibility = Visibility.PRIVATE
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    contents: Optional[List[Dict[str, Any]]] = None

@dataclass
class KnowledgeItemUpdateInput:
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    visibility: Optional[Visibility] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    status: Optional[KnowledgeItemStatusEnum] = None
    contents: Optional[List[Dict[str, Any]]] = None
    conditions: Optional[Dict[str, Any]] = None  # Conditions for item update
    content_conditions: Optional[Dict[str, Dict[str, Any]]] = None  # Conditions per content_type
    output_fields: Optional[List[str]] = None  # Fields to include in output

@dataclass
class KnowledgeItemOutput:
    id: str
    title: str
    item_type: KnowledgeItemTypeEnum
    status: KnowledgeItemStatusEnum
    visibility: Visibility
    created_by: str
    created_at: datetime
    updated_at: datetime
    tenant_id: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    contents: Optional[List[Dict[str, Any]]] = None

class KnowledgeItemService:
    """Knowledge Item Service with integrated content management"""

    def __init__(self):
        self.item_repo = KnowledgeItemRepository()

    async def create_knowledge_item(self, item_data: KnowledgeItemInput) -> Optional[KnowledgeItemOutput]:
        """Create knowledge item with its contents"""
        repo_input = {
            "title": item_data.title,
            "item_type": item_data.item_type,
            "tenant_id": item_data.tenant_id,
            "created_by": item_data.created_by,
            "description": item_data.description,
            "tags": item_data.tags or [],
            "category": item_data.category,
            "metadata": item_data.metadata or {},
            "visibility": item_data.visibility,
            "allowed_users": item_data.allowed_users or [],
            "allowed_roles": item_data.allowed_roles or [],
            "status": KnowledgeItemStatusEnum.CREATED,
            "contents": item_data.contents or []
        }
        
        result = await self.item_repo.create_item(repo_input)
        if not result:
            return None
            
        return KnowledgeItemOutput(**result)

    async def get_knowledge_item(self, item_id: str, tenant_id: str, user_id: str, user_roles: List[str], query_conditions: Optional[Dict[str, Any]] = None, output_fields: Optional[List[str]] = None) -> Optional[KnowledgeItemOutput]:
        """Get knowledge item with access check, conditions, and field projection"""
        item = await self.item_repo.get_item(item_id, tenant_id, query_conditions, output_fields)
        if not item or not self._has_access(item, user_id, user_roles):
            return None
        return KnowledgeItemOutput(**item)

    async def update_knowledge_item(self, item_id: str, tenant_id: str, update_data: KnowledgeItemUpdateInput, user_id: str, user_roles: List[str]) -> Optional[KnowledgeItemOutput]:
        """Update knowledge item and its contents with access check and conditional logic"""
        current_item = await self.item_repo.get_item(item_id, tenant_id)
        if not current_item or not self._has_access(current_item, user_id, user_roles):
            return None

        repo_update = {k: v for k, v in update_data.__dict__.items() if v is not None and k not in ["conditions", "content_conditions", "output_fields"]}

        # Handle batch content updates (upsert: update existing, create new)
        if update_data.contents is not None:
            repo_update["contents"] = [
                {**content, "created_by": current_item["created_by"]}
                for content in update_data.contents
            ]
            repo_update["content_conditions"] = update_data.content_conditions or {}

        result = await self.item_repo.update_item(item_id, tenant_id, repo_update, update_data.conditions)
        if not result:
            return None

        # Apply output field projection for the result
        if update_data.output_fields:
            filtered_result = {k: v for k, v in result.items() if k in update_data.output_fields}
            if "contents" in result and "contents" in update_data.output_fields:
                filtered_result["contents"] = [
                    {k: v for k, v in content.items() if k in update_data.output_fields}
                    for content in result["contents"]
                ]
            result = filtered_result

        return KnowledgeItemOutput(**result)

    async def delete_knowledge_item(self, item_id: str, tenant_id: str, user_id: str, user_roles: List[str]) -> bool:
        """Delete knowledge item and its contents with access check"""
        item = await self.item_repo.get_item(item_id, tenant_id)
        if not item or not self._has_access(item, user_id, user_roles):
            return False
        return await self.item_repo.delete_item(item_id, tenant_id)

    async def list_knowledge_items(
        self,
        tenant_id: str,
        user_id: str,
        user_roles: List[str],
        query_conditions: Optional[Dict[str, Any]] = None,
        output_fields: Optional[List[str]] = None,
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
    ) -> List[KnowledgeItemOutput]:
        """List knowledge items with access filtering, conditions, and field projection"""
        items = await self.item_repo.list_items(
            tenant_id=tenant_id,
            query_conditions=query_conditions,
            output_fields=output_fields,
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
        return [
            KnowledgeItemOutput(**item)
            for item in items
            if self._has_access(item, user_id, user_roles)
        ]

    async def count_knowledge_items(
        self,
        tenant_id: str,
        user_id: str,
        user_roles: List[str],
        query_conditions: Optional[Dict[str, Any]] = None,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[KnowledgeItemStatusEnum] = None,
        visibility: Optional[Visibility] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> int:
        """Count accessible knowledge items based on conditions"""
        items = await self.item_repo.list_items(
            tenant_id=tenant_id,
            query_conditions=query_conditions,
            output_fields=["id"],  # Minimal fields for counting
            item_type=item_type,
            status=status,
            visibility=visibility,
            created_by=created_by,
            tags=tags,
            category=category,
            search_text=search_text,
            page=1,
            page_size=999999,  # Large number to get all items for counting
            sort_by="created_at",
            sort_order="desc"
        )
        return len([item for item in items if self._has_access(item, user_id, user_roles)])

    async def get_item_content_versions(
        self,
        item_id: str,
        content_type: ItemContentTypeEnum,
        tenant_id: str,
        user_id: str,
        user_roles: List[str],
        page: int = 1,
        page_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Get content versions for an item with access check"""
        item = await self.item_repo.get_item(item_id, tenant_id)
        if not item or not self._has_access(item, user_id, user_roles):
            return []
        
        contents = await self.item_repo.content_repo.get_content_versions(item_id, content_type, tenant_id, page, page_size)
        return [content.dict() for content in contents]

    def _has_access(self, item: Dict[str, Any], user_id: str, user_roles: List[str]) -> bool:
        """Check if user has access to the item"""
        if item["visibility"] == Visibility.PUBLIC:
            return True
        if item["created_by"] == user_id:
            return True
        if user_id in item.get("allowed_users", []):
            return True
        if any(role in item.get("allowed_roles", []) for role in user_roles):
            return True
        return False

knowledge_item_service = KnowledgeItemService()