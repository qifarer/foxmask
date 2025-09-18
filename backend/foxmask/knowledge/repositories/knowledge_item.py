# -*- coding: utf-8 -*-
# foxmask/knowledge/repositories/knowledge_item.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from beanie.operators import In, Eq, And, Or, Text
from pymongo import ASCENDING, DESCENDING

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
    """知识条目数据访问层"""
    
    async def create_item(self, item_data: dict) -> KnowledgeItem:
        """创建知识条目"""
        item = KnowledgeItem(**item_data)
        return await item.insert()
    
    async def get_item_by_id(self, item_id: str, tenant_id: str) -> Optional[KnowledgeItem]:
        """根据ID获取知识条目"""
        try:
            object_id = PydanticObjectId(item_id)
            return await KnowledgeItem.find_one(
                KnowledgeItem.id == object_id,
                KnowledgeItem.tenant_id == tenant_id
            )
        except:
            return None
    
    async def get_items_by_ids(self, item_ids: List[str], tenant_id: str) -> List[KnowledgeItem]:
        """根据ID列表获取多个知识条目"""
        try:
            object_ids = [PydanticObjectId(item_id) for item_id in item_ids]
            return await KnowledgeItem.find(
                In(KnowledgeItem.id, object_ids),
                KnowledgeItem.tenant_id == tenant_id
            ).to_list()
        except:
            return []
    
    async def update_item(self, item_id: str, tenant_id: str, update_data: dict) -> Optional[KnowledgeItem]:
        """更新知识条目"""
        item = await self.get_item_by_id(item_id, tenant_id)
        if not item:
            return None
        
        # 排除不可更新的字段
        update_data.pop("id", None)
        update_data.pop("created_at", None)
        update_data.pop("created_by", None)
        update_data.pop("tenant_id", None)
        
        # 设置更新时间
        update_data["updated_at"] = get_current_time()
        
        await item.set(update_data)
        return item
    
    async def delete_item(self, item_id: str, tenant_id: str) -> bool:
        """删除知识条目"""
        item = await self.get_item_by_id(item_id, tenant_id)
        if not item:
            return False
        
        await item.delete()
        return True
    
    async def list_items(
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
        """分页查询知识条目列表"""
        query_filters = [Eq(KnowledgeItem.tenant_id, tenant_id)]
        
        # 添加过滤条件
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
        
        # 文本搜索
        if search_text:
            query_filters.append(Text(KnowledgeItem.title, search_text))
        
        # 构建查询
        query = KnowledgeItem.find(And(*query_filters))
        
        # 排序
        sort_field = getattr(KnowledgeItem, sort_by)
        sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
        query = query.sort((sort_field, sort_direction))
        
        # 分页
        skip = (page - 1) * page_size
        return await query.skip(skip).limit(page_size).to_list()
    
    async def count_items(
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
        
        return await KnowledgeItem.find(And(*query_filters)).count()
    
    async def update_item_status(
        self, 
        item_id: str, 
        tenant_id: str, 
        status: KnowledgeItemStatusEnum,
        processing_metadata: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> Optional[KnowledgeItem]:
        """更新知识条目状态"""
        item = await self.get_item_by_id(item_id, tenant_id)
        if not item:
            return None
        
        update_data = {
            "status": status,
            "updated_at": get_current_time()
        }
        
        if processing_metadata:
            if item.processing_metadata:
                item.processing_metadata.update(processing_metadata)
            else:
                item.processing_metadata = processing_metadata
            update_data["processing_metadata"] = item.processing_metadata
        
        if error_info:
            update_data["error_info"] = error_info
        
        await item.set(update_data)
        return item
    
    async def add_tag_to_item(self, item_id: str, tenant_id: str, tag: str) -> Optional[KnowledgeItem]:
        """为知识条目添加标签"""
        item = await self.get_item_by_id(item_id, tenant_id)
        if not item:
            return None
        
        item.add_tag(tag)
        await item.save()
        return item
    
    async def remove_tag_from_item(self, item_id: str, tenant_id: str, tag: str) -> Optional[KnowledgeItem]:
        """从知识条目移除标签"""
        item = await self.get_item_by_id(item_id, tenant_id)
        if not item:
            return None
        
        item.remove_tag(tag)
        await item.save()
        return item


class KnowledgeItemContentRepository:
    """知识条目内容数据访问层"""
    
    async def create_content(self, content_data: dict) -> KnowledgeItemContent:
        """创建知识条目内容"""
        content = KnowledgeItemContent(**content_data)
        return await content.insert()
    
    async def get_content_by_id(self, content_id: str, tenant_id: str) -> Optional[KnowledgeItemContent]:
        """根据ID获取内容"""
        try:
            object_id = PydanticObjectId(content_id)
            return await KnowledgeItemContent.find_one(
                KnowledgeItemContent.id == object_id,
                KnowledgeItemContent.tenant_id == tenant_id
            )
        except:
            return None
    
    async def get_latest_content(
        self, 
        item_id: str, 
        content_type: ItemContentTypeEnum,
        tenant_id: str
    ) -> Optional[KnowledgeItemContent]:
        """获取指定类型的最新内容"""
        return await KnowledgeItemContent.find_one(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.content_type == content_type,
            KnowledgeItemContent.is_latest == True,
            KnowledgeItemContent.tenant_id == tenant_id
        ).sort(-KnowledgeItemContent.version)
    
    async def get_content_versions(
        self, 
        item_id: str, 
        content_type: ItemContentTypeEnum,
        tenant_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> List[KnowledgeItemContent]:
        """获取内容的所有版本"""
        skip = (page - 1) * page_size
        return await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.content_type == content_type,
            KnowledgeItemContent.tenant_id == tenant_id
        ).sort(-KnowledgeItemContent.version).skip(skip).limit(page_size).to_list()
    
    async def update_content(
        self, 
        content_id: str, 
        tenant_id: str, 
        update_data: dict
    ) -> Optional[KnowledgeItemContent]:
        """更新内容"""
        content = await self.get_content_by_id(content_id, tenant_id)
        if not content:
            return None
        
        # 排除不可更新的字段
        update_data.pop("id", None)
        update_data.pop("created_at", None)
        update_data.pop("created_by", None)
        update_data.pop("tenant_id", None)
        update_data.pop("item_id", None)
        
        update_data["updated_at"] = get_current_time()
        
        await content.set(update_data)
        return content
    
    async def mark_previous_versions_not_latest(self, item_id: str, content_type: ItemContentTypeEnum, tenant_id: str):
        """将旧版本标记为非最新"""
        await KnowledgeItemContent.find(
            KnowledgeItemContent.item_id == item_id,
            KnowledgeItemContent.content_type == content_type,
            KnowledgeItemContent.is_latest == True,
            KnowledgeItemContent.tenant_id == tenant_id
        ).update({"$set": {"is_latest": False, "updated_at": get_current_time()}})
    
    async def create_new_content_version(
        self, 
        content_data: dict,
        tenant_id: str
    ) -> KnowledgeItemContent:
        """创建新版本内容"""
        # 获取当前最新版本以确定新版本号
        latest_content = await self.get_latest_content(
            content_data["item_id"], 
            content_data["content_type"],
            tenant_id
        )
        
        if latest_content:
            content_data["version"] = latest_content.version + 1
            # 将旧版本标记为非最新
            await self.mark_previous_versions_not_latest(
                content_data["item_id"], 
                content_data["content_type"],
                tenant_id
            )
        
        return await self.create_content(content_data)

knowledge_item_repository = KnowledgeItemRepository()
knowledge_item_content_repository = KnowledgeItemContentRepository()
