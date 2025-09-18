# -*- coding: utf-8 -*-
# foxmask/knowledge/repositories/knowledge_item_repository.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId, WriteRules
from beanie.operators import In, Eq, And, Text
from pymongo import ASCENDING, DESCENDING
from datetime import datetime

from foxmask.knowledge.models import (
    KnowledgeItem, 
    KnowledgeItemStatusEnum, 
    KnowledgeItemTypeEnum,
    KnowledgeItemContent,
    ItemContentTypeEnum
)
from foxmask.core.model import Visibility
from foxmask.utils.helpers import get_current_time

class KnowledgeItemRepository:
    """Knowledge Item Repository with integrated content management"""
    
    def __init__(self):
        self.content_repo = KnowledgeItemContentRepository()

    async def create_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create knowledge item with its contents atomically"""
        async with await KnowledgeItem.get_motor_client().start_session() as session:
            async with session.start_transaction():
                try:
                    # Extract content data if present
                    contents_data = item_data.pop("contents", [])
                    
                    # Create main item
                    item_data["created_at"] = item_data["updated_at"] = get_current_time()
                    item = KnowledgeItem(**item_data)
                    await item.insert(session=session)
                    
                    # Create contents
                    contents = []
                    for content_data in contents_data:
                        content_data.update({
                            "item_id": str(item.id),
                            "tenant_id": item_data["tenant_id"],
                            "version": 1,
                            "is_latest": True,
                            "created_at": get_current_time(),
                            "updated_at": get_current_time()
                        })
                        content = await self.content_repo.create_content(content_data, session=session)
                        contents.append(content.dict())
                    
                    return {
                        **item.dict(),
                        "contents": contents
                    }
                except Exception:
                    return None

    async def get_item(self, item_id: str, tenant_id: str, query_conditions: Optional[Dict[str, Any]] = None, output_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Get knowledge item with its latest contents, applying conditions and field projection"""
        try:
            query_filters = [
                Eq(KnowledgeItem.id, PydanticObjectId(item_id)),
                Eq(KnowledgeItem.tenant_id, tenant_id)
            ]
            if query_conditions:
                for key, value in query_conditions.items():
                    if key != "contents" and hasattr(KnowledgeItem, key):
                        query_filters.append(Eq(getattr(KnowledgeItem, key), value))

            projection = {field: 1 for field in output_fields} if output_fields else None
            item = await KnowledgeItem.find_one(
                And(*query_filters),
                projection=projection
            )
            if not item:
                return None

            content_conditions = query_conditions.get("contents", {}) if query_conditions else {}
            contents = await self.content_repo.get_latest_contents(
                item_id, tenant_id, content_conditions, output_fields
            )
            item_dict = item.dict()
            item_dict["contents"] = [content.dict() for content in contents]
            return item_dict
        except:
            return None

    async def update_item(self, item_id: str, tenant_id: str, update_data: Dict[str, Any], conditions: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Update knowledge item and its contents atomically with conditional logic"""
        async with await KnowledgeItem.get_motor_client().start_session() as session:
            async with session.start_transaction():
                item = await KnowledgeItem.find_one(
                    KnowledgeItem.id == PydanticObjectId(item_id),
                    KnowledgeItem.tenant_id == tenant_id,
                    session=session
                )
                if not item:
                    return None

                # Check conditions for item update
                item_update = {}
                if conditions:
                    item_dict = item.dict()
                    if all(item_dict.get(k) == v for k, v in conditions.items() if k in item_dict):
                        item_update = {k: v for k, v in update_data.items() if k not in 
                            ["id", "created_at", "created_by", "tenant_id", "contents"]}
                else:
                    item_update = {k: v for k, v in update_data.items() if k not in 
                        ["id", "created_at", "created_by", "tenant_id", "contents"]}

                if item_update:
                    item_update["updated_at"] = get_current_time()
                    await item.set(item_update, session=session)

                # Handle batch content updates with conditions
                contents = []
                content_conditions = update_data.get("content_conditions", {})
                if "contents" in update_data:
                    for content_data in update_data["contents"]:
                        content = await self.content_repo.upsert_content_version(
                            {
                                **content_data,
                                "item_id": item_id,
                                "tenant_id": tenant_id,
                                "created_by": item.created_by
                            },
                            tenant_id,
                            content_conditions.get(content_data["content_type"], {}),
                            session=session
                        )
                        contents.append(content.dict())

                return {
                    **item.dict(),
                    "contents": contents
                }

    async def delete_item(self, item_id: str, tenant_id: str) -> bool:
        """Delete knowledge item and all its contents atomically"""
        async with await KnowledgeItem.get_motor_client().start_session() as session:
            async with session.start_transaction():
                item = await KnowledgeItem.find_one(
                    KnowledgeItem.id == PydanticObjectId(item_id),
                    KnowledgeItem.tenant_id == tenant_id,
                    session=session
                )
                if not item:
                    return False

                await self.content_repo.delete_all_contents(item_id, tenant_id, session=session)
                await item.delete(session=session)
                return True

    async def list_items(
        self,
        tenant_id: str,
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
    ) -> List[Dict[str, Any]]:
        """List knowledge items with their latest contents, applying conditions and field projection"""
        query_filters = [Eq(KnowledgeItem.tenant_id, tenant_id)]
        
        if item_type:
            query_filters.append(Eq(KnowledgeItem.item_type, item_type))
        if status:
            query_filters.append(Eq(KnowledgeItem.status, status))
        if visibility:
            query_filters.append(Eq(KnowledgeItem.visibility, visibility))
        if created_by:
            query_filters.append(Eq(KnowledgeItem.created_by, created_by))
        if category:
            query_filters.append(Eq(KnowledgeItem.category, category))
        if tags:
            query_filters.append(In(KnowledgeItem.tags, tags))
        if search_text:
            query_filters.append(Text(KnowledgeItem.title, search_text))
        if query_conditions:
            for key, value in query_conditions.items():
                if key != "contents" and hasattr(KnowledgeItem, key):
                    query_filters.append(Eq(getattr(KnowledgeItem, key), value))

        projection = {field: 1 for field in output_fields} if output_fields else None
        query = KnowledgeItem.find(And(*query_filters), projection=projection)
        sort_field = getattr(KnowledgeItem, sort_by)
        sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
        query = query.sort((sort_field, sort_direction))

        skip = max(0, (page - 1) * page_size)
        items = await query.skip(skip).limit(page_size).to_list()

        content_conditions = query_conditions.get("contents", {}) if query_conditions else {}
        results = []
        for item in items:
            contents = await self.content_repo.get_latest_contents(
                str(item.id), tenant_id, content_conditions, output_fields
            )
            item_dict = item.dict()
            item_dict["contents"] = [content.dict() for content in contents]
            results.append(item_dict)

        return results

    async def count_items(
        self,
        tenant_id: str,
        query_conditions: Optional[Dict[str, Any]] = None,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[KnowledgeItemStatusEnum] = None,
        visibility: Optional[Visibility] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> int:
        """Count knowledge items based on conditions"""
        query_filters = [Eq(KnowledgeItem.tenant_id, tenant_id)]
        
        if item_type:
            query_filters.append(Eq(KnowledgeItem.item_type, item_type))
        if status:
            query_filters.append(Eq(KnowledgeItem.status, status))
        if visibility:
            query_filters.append(Eq(KnowledgeItem.visibility, visibility))
        if created_by:
            query_filters.append(Eq(KnowledgeItem.created_by, created_by))
        if category:
            query_filters.append(Eq(KnowledgeItem.category, category))
        if tags:
            query_filters.append(In(KnowledgeItem.tags, tags))
        if search_text:
            query_filters.append(Text(KnowledgeItem.title, search_text))
        if query_conditions:
            for key, value in query_conditions.items():
                if key != "contents" and hasattr(KnowledgeItem, key):
                    query_filters.append(Eq(getattr(KnowledgeItem, key), value))
        
        return await KnowledgeItem.find(And(*query_filters)).count()


class KnowledgeItemContentRepository:
    """Knowledge Item Content Repository"""
    
    async def create_content(self, content_data: Dict[str, Any], session=None) -> KnowledgeItemContent:
        """Create knowledge item content"""
        content = KnowledgeItemContent(**content_data)
        return await content.insert(session=session)

    async def get_latest_contents(self, item_id: str, tenant_id: str, content_conditions: Dict[str, Dict[str, Any]] = None, output_fields: Optional[List[str]] = None) -> List[KnowledgeItemContent]:
        """Get latest contents for an item, applying conditions and field projection"""
        query_filters = [
            Eq(KnowledgeItemContent.item_id, item_id),
            Eq(KnowledgeItemContent.tenant_id, tenant_id),
            Eq(KnowledgeItemContent.is_latest, True)
        ]
        
        if content_conditions:
            for content_type, conditions in content_conditions.items():
                content_filters = [
                    Eq(KnowledgeItemContent.content_type, content_type)
                ]
                for key, value in conditions.items():
                    if hasattr(KnowledgeItemContent, key):
                        content_filters.append(Eq(getattr(KnowledgeItemContent, key), value))
                query_filters.append(And(*content_filters))

        projection = {field: 1 for field in output_fields} if output_fields else None
        return await KnowledgeItemContent.find(
            And(*query_filters),
            projection=projection
        ).sort(-KnowledgeItemContent.version).to_list()

    async def get_content_versions(
        self, 
        item_id: str, 
        content_type: ItemContentTypeEnum,
        tenant_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> List[KnowledgeItemContent]:
        """Get all versions of a specific content type for an item"""
        skip = (page - 1) * page_size
        return await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.content_type == content_type,
            KnowledgeItemContent.tenant_id == tenant_id
        ).sort(-KnowledgeItemContent.version).skip(skip).limit(page_size).to_list()

    async def upsert_content_version(self, content_data: Dict[str, Any], tenant_id: str, conditions: Dict[str, Any], session=None) -> KnowledgeItemContent:
        """Upsert content version based on item_id and content_type with conditions"""
        latest_content = await KnowledgeItemContent.find_one(
            KnowledgeItemContent.item_id == content_data["item_id"],
            KnowledgeItemContent.content_type == content_data["content_type"],
            KnowledgeItemContent.is_latest == True,
            KnowledgeItemContent.tenant_id == tenant_id,
            session=session
        )

        # Check conditions for content update
        should_update = True
        if conditions and latest_content:
            content_dict = latest_content.dict()
            should_update = all(content_dict.get(k) == v for k, v in conditions.items() if k in content_dict)

        if not should_update:
            # If conditions not met and content exists, return the latest content without updating
            return latest_content if latest_content else await self.create_content(content_data, session=session)

        if latest_content:
            # Mark existing latest content as non-latest
            await KnowledgeItemContent.find(
                KnowledgeItemContent.item_id == content_data["item_id"],
                KnowledgeItemContent.content_type == content_data["content_type"],
                KnowledgeItemContent.is_latest == True,
                KnowledgeItemContent.tenant_id == tenant_id,
                session=session
            ).update({"$set": {"is_latest": False, "updated_at": get_current_time()}}, session=session)

        content_data.update({
            "version": latest_content.version + 1 if latest_content else 1,
            "is_latest": True,
            "created_at": get_current_time(),
            "updated_at": get_current_time()
        })

        return await self.create_content(content_data, session=session)

    async def delete_all_contents(self, item_id: str, tenant_id: str, session=None):
        """Delete all contents for an item"""
        await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.tenant_id == tenant_id,
            session=session
        ).delete()

knowledge_item_repository = KnowledgeItemRepository()
knowledge_item_content_repository = KnowledgeItemContentRepository()
