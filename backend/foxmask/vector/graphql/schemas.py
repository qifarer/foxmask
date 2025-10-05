# graphql/schema.py
import strawberry
from typing import List, Optional
from datetime import datetime

from foxmask.knowledge_item.domain import (
    KnowledgeItemTypeEnum, KnowledgeItemStatusEnum, ItemContentTypeEnum
)

@strawberry.type
class KnowledgeItemContentType:
    id: str
    content_id: str
    item_id: str
    content_type: ItemContentTypeEnum
    content_data: strawberry.scalars.JSON
    version: int
    is_latest: bool
    metadata: strawberry.scalars.JSON
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    vector_model: Optional[str]
    chunk_index: Optional[int]
    total_chunks: Optional[int]

@strawberry.type
class KnowledgeItemType:
    id: str
    item_id: str
    item_type: KnowledgeItemTypeEnum
    status: KnowledgeItemStatusEnum
    title: str
    description: Optional[str]
    metadata: strawberry.scalars.JSON
    tags: List[str]
    tenant_id: Optional[str]
    visibility: str
    created_by: Optional[str]
    allowed_users: List[str]
    allowed_roles: List[str]
    created_at: datetime
    updated_at: datetime

@strawberry.type
class KnowledgeItemWithContentsType:
    item: KnowledgeItemType
    contents: List[KnowledgeItemContentType]

@strawberry.type
class SearchResultType:
    items: List[KnowledgeItemWithContentsType]
    total_count: int
    search_time: float

@strawberry.type
class FileProcessingResultType:
    item_id: str
    content_ids: List[str]
    status: KnowledgeItemStatusEnum
    processing_time: float

@strawberry.input
class KnowledgeItemCreateInput:
    item_type: KnowledgeItemTypeEnum
    title: str
    description: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    tags: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    visibility: Optional[str] = "public"
    created_by: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None

@strawberry.input
class KnowledgeItemUpdateInput:
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    tags: Optional[List[str]] = None
    status: Optional[KnowledgeItemStatusEnum] = None

@strawberry.input
class KnowledgeItemContentCreateInput:
    item_id: str
    content_type: ItemContentTypeEnum
    content_data: strawberry.scalars.JSON
    version: Optional[int] = 1
    is_latest: Optional[bool] = True
    metadata: Optional[strawberry.scalars.JSON] = None
    created_by: Optional[str] = None
    vector_model: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None

@strawberry.input
class SearchFiltersInput:
    item_type: Optional[KnowledgeItemTypeEnum] = None
    status: Optional[KnowledgeItemStatusEnum] = None
    tags: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    created_by: Optional[str] = None

@strawberry.input
class FileProcessingRequestInput:
    file_name: str
    file_content: str
    file_type: str
    metadata: Optional[strawberry.scalars.JSON] = None

