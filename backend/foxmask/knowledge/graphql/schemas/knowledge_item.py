import strawberry
from typing import List, Optional
from strawberry.scalars import JSON
from foxmask.knowledge.models.knowledge_item import KnowledgeItemTypeEnum, ItemChunkTypeEnum
from foxmask.core.model import Visibility, Status


# 枚举类型 Schema


# 基础输入输出类型
@strawberry.input
class KnowledgeItemCreateInput:
    uid: str
    tenant_id: str
    item_type: KnowledgeItemTypeEnum
    source_id: Optional[str] = None
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_by: Optional[str] = None
    allowed_users: Optional[List[str]] = strawberry.field(default_factory=list)
    allowed_roles: Optional[List[str]] = strawberry.field(default_factory=list)
    proc_meta: Optional[JSON] = None
    metadata: Optional[JSON] = None


@strawberry.input
class KnowledgeItemUpdateInput:
    uid: Optional[str] = None
    tenant_id: Optional[str] = None
    item_type: Optional[KnowledgeItemTypeEnum] = None
    source_id: Optional[str] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    created_by: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    proc_meta: Optional[JSON] = None
    error_info: Optional[JSON] = None
    metadata: Optional[JSON] = None


@strawberry.input
class KnowledgeItemQueryInput:
    tenant_id: Optional[str] = None
    item_type: Optional[KnowledgeItemTypeEnum] = None
    status: Optional[Status] = None
    visibility: Optional[Visibility] = None
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None


@strawberry.type
class KnowledgeItemSchema:
    id: Optional[str]
    uid: str
    tenant_id: str
    item_type: KnowledgeItemTypeEnum
    source_id: Optional[str]
    title: str
    desc: Optional[str]
    category: Optional[str]
    tags: List[str]
    note: Optional[str]
    status: Status
    visibility: Visibility
    created_at: str
    updated_at: str
    archived_at: Optional[str]
    created_by: Optional[str]
    allowed_users: List[str]
    allowed_roles: List[str]
    proc_meta: JSON
    error_info: Optional[JSON]
    metadata: JSON


@strawberry.input
class KnowledgeItemInfoCreateInput:
    uid: str
    tenant_id: str
    master_id: str
    page_idx: int
    page_size: Optional[JSON] = None
    preproc_blocks: Optional[List[JSON]] = strawberry.field(default_factory=list)
    para_blocks: Optional[List[JSON]] = strawberry.field(default_factory=list)
    discarded_blocks: Optional[List[JSON]] = strawberry.field(default_factory=list)
    note: Optional[str] = None


@strawberry.type
class KnowledgeItemInfoSchema:
    id: Optional[str]
    uid: str
    tenant_id: str
    master_id: str
    page_idx: int
    page_size: JSON
    preproc_blocks: List[JSON]
    para_blocks: List[JSON]
    discarded_blocks: List[JSON]
    note: Optional[str]
    created_at: str
    updated_at: str


@strawberry.input
class KnowledgeItemChunkCreateInput:
    uid: str
    tenant_id: str
    master_id: str
    chunk_idx: int
    chunk_type: ItemChunkTypeEnum
    text: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None
    equation: Optional[str] = None
    table_data: Optional[List[JSON]] = None
    code_content: Optional[str] = None
    code_language: Optional[str] = None
    chunk_metadata: Optional[JSON] = None
    position: Optional[JSON] = None
    size: Optional[JSON] = None
    vector_id: Optional[str] = None


@strawberry.type
class KnowledgeItemChunkSchema:
    id: Optional[str]
    uid: str
    tenant_id: str
    master_id: str
    chunk_idx: int
    chunk_type: ItemChunkTypeEnum
    text: Optional[str]
    image_url: Optional[str]
    image_data: Optional[str]
    equation: Optional[str]
    table_data: Optional[List[JSON]]
    code_content: Optional[str]
    code_language: Optional[str]
    chunk_metadata: JSON
    position: JSON
    size: JSON
    vector_id: Optional[str]
    created_at: str
    updated_at: str


# 组合操作类型
@strawberry.input
class KnowledgeItemWithInfosCreateInput:
    item: KnowledgeItemCreateInput
    infos: List[KnowledgeItemInfoCreateInput] = strawberry.field(default_factory=list)


@strawberry.input
class KnowledgeItemChunkingInput:
    item_id: str
    chunks: List[KnowledgeItemChunkCreateInput]
    update_metadata: Optional[JSON] = None


@strawberry.input
class KnowledgeItemWithDetailsQueryInput:
    item_id: Optional[str] = None
    uid: Optional[str] = None
    tenant_id: str
    include_infos: bool = False
    include_chunks: bool = False
    info_page_idx: Optional[int] = None
    chunk_types: Optional[List[ItemChunkTypeEnum]] = None


@strawberry.input
class BatchDeleteInput:
    item_ids: List[str]


@strawberry.type
class KnowledgeItemPageInfo:
    items: List[KnowledgeItemSchema]
    total: int
    page: int
    size: int
    has_next: bool
    has_previous: bool


@strawberry.type
class MutationResult:
    success: bool
    message: Optional[str] = None
    item_id: Optional[str] = None


@strawberry.type
class KnowledgeItemWithInfosCreateResult:
    success: bool
    message: Optional[str] = None
    item: Optional[KnowledgeItemSchema] = None
    infos: List[KnowledgeItemInfoSchema] = strawberry.field(default_factory=list)


@strawberry.type
class KnowledgeItemChunkingResult:
    success: bool
    message: Optional[str] = None
    item: Optional[KnowledgeItemSchema] = None
    chunks: List[KnowledgeItemChunkSchema] = strawberry.field(default_factory=list)


@strawberry.type
class KnowledgeItemWithDetailsSchema:
    item: KnowledgeItemSchema
    infos: List[KnowledgeItemInfoSchema] = strawberry.field(default_factory=list)
    chunks: List[KnowledgeItemChunkSchema] = strawberry.field(default_factory=list)


@strawberry.type
class BatchOperationResult:
    success: bool
    message: Optional[str] = None
    total_count: int
    success_count: int
    failed_count: int
    failed_items: List[str] = strawberry.field(default_factory=list)