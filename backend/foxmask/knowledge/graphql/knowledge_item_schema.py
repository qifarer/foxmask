# -*- coding: utf-8 -*-
# foxmask/knowledge/schemas/knowledge_item_schema.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

import strawberry
from typing import List, Optional

from foxmask.knowledge.models import (
    KnowledgeItem, 
    KnowledgeItemStatusEnum, 
    KnowledgeItemTypeEnum,
    ItemContentTypeEnum
)

from foxmask.core.model import Visibility


# GraphQL 输入类型
@strawberry.input
class KnowledgeItemInput:
    title: str
    item_type: KnowledgeItemTypeEnum
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    visibility: Visibility = Visibility.PRIVATE
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    content: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class KnowledgeItemUpdateInput:
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    visibility: Optional[Visibility] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    content: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class KnowledgeItemContentInput:
    content_type: ItemContentTypeEnum
    content_data: strawberry.scalars.JSON
    processing_metadata: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class KnowledgeItemFilter:
    item_type: Optional[KnowledgeItemTypeEnum] = None
    status: Optional[KnowledgeItemStatusEnum] = None
    visibility: Optional[Visibility] = None
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    search_text: Optional[str] = None

@strawberry.input
class PaginationInput:
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

@strawberry.input
class BatchItemIdsInput:
    item_ids: List[str]


# GraphQL 类型
@strawberry.type
class KnowledgeItemType:
    id: str
    title: str
    item_type: KnowledgeItemTypeEnum
    status: KnowledgeItemStatusEnum
    description: Optional[str]
    tags: List[str]
    category: Optional[str]
    metadata: strawberry.scalars.JSON
    tenant_id: str
    visibility: Visibility
    allowed_users: List[str]
    allowed_roles: List[str]
    content: strawberry.scalars.JSON
    processing_metadata: strawberry.scalars.JSON
    error_info: Optional[strawberry.scalars.JSON]
    created_at: str
    updated_at: str
    created_by: str

    @classmethod
    def from_model(cls, model: KnowledgeItem):
        return cls(
            id=str(model.id),
            title=model.title,
            item_type=model.item_type,
            status=model.status,
            description=model.description,
            tags=model.tags,
            category=model.category,
            metadata=model.metadata,
            tenant_id=model.tenant_id,
            visibility=model.visibility,
            allowed_users=model.allowed_users,
            allowed_roles=model.allowed_roles,
            content=model.content,
            processing_metadata=model.processing_metadata,
            error_info=model.error_info,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
            created_by=model.created_by
        )


@strawberry.type
class KnowledgeItemList:
    items: List[KnowledgeItemType]
    total_count: int
    page: int
    page_size: int
    has_next: bool


# 添加缺失的 Mutation 响应类型
@strawberry.type
class MutationKnowledgeItemResponse:
    """知识条目变更操作响应"""
    success: bool
    message: Optional[str] = None
    item: Optional[KnowledgeItemType] = None
    content: Optional[strawberry.scalars.JSON] = None  # 如果需要返回内容数据