from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from foxmask.knowledge.models.knowledge_item import KnowledgeItemTypeEnum, ItemChunkTypeEnum
from foxmask.core.model import Visibility, Status


class KnowledgeItemCreateDTO(BaseModel):
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    item_type: KnowledgeItemTypeEnum = Field(..., description="知识条目类型")
    source_id: Optional[str] = Field(None, description="源ID")
    title: str = Field(..., description="标题", min_length=1, max_length=300)
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    status: Status = Field(default=Status.DRAFT, description="记录状态")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="知识可用性级别")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    proc_meta: Dict[str, Any] = Field(default_factory=dict, description="处理过程元数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")


class KnowledgeItemUpdateDTO(BaseModel):
    uid: Optional[str] = Field(None, description="UID")
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    item_type: Optional[KnowledgeItemTypeEnum] = Field(None, description="知识条目类型")
    source_id: Optional[str] = Field(None, description="源ID")
    title: Optional[str] = Field(None, description="标题", min_length=1, max_length=300)
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签")
    note: Optional[str] = Field(None, description="备注")
    status: Optional[Status] = Field(None, description="记录状态")
    visibility: Optional[Visibility] = Field(None, description="知识可用性级别")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    allowed_users: Optional[List[str]] = Field(None, description="有访问权限的用户ID列表")
    allowed_roles: Optional[List[str]] = Field(None, description="有访问权限的角色列表")
    proc_meta: Optional[Dict[str, Any]] = Field(None, description="处理过程元数据")
    error_info: Optional[Dict[str, Any]] = Field(None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定义元数据")


class KnowledgeItemQueryDTO(BaseModel):
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    item_type: Optional[KnowledgeItemTypeEnum] = Field(None, description="知识条目类型")
    status: Optional[Status] = Field(None, description="记录状态")
    visibility: Optional[Visibility] = Field(None, description="知识可用性级别")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_by: Optional[str] = Field(None, description="创建者用户ID")


class KnowledgeItemDTO(BaseModel):
    id: Optional[PydanticObjectId] = None
    uid: str
    tenant_id: str
    item_type: KnowledgeItemTypeEnum
    source_id: Optional[str] = None
    title: str
    desc: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    status: Status = Status.DRAFT
    visibility: Visibility = Visibility.PUBLIC
    created_at: str
    updated_at: str
    archived_at: Optional[str] = None
    created_by: Optional[str] = None
    allowed_users: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    proc_meta: Dict[str, Any] = Field(default_factory=dict)
    error_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeItemInfoCreateDTO(BaseModel):
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    master_id: str = Field(..., description="主文档ID")
    page_idx: int = Field(..., ge=0, description="页码索引")
    page_size: Dict[str, Any] = Field(default_factory=dict, description="页面尺寸信息")
    preproc_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="预处理块列表")
    para_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="段落块列表")
    discarded_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="丢弃块列表")
    note: Optional[str] = Field(None, description="备注")


class KnowledgeItemInfoUpdateDTO(BaseModel):
    uid: Optional[str] = Field(None, description="UID")
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    master_id: Optional[str] = Field(None, description="主文档ID")
    page_idx: Optional[int] = Field(None, ge=0, description="页码索引")
    page_size: Optional[Dict[str, Any]] = Field(None, description="页面尺寸信息")
    preproc_blocks: Optional[List[Dict[str, Any]]] = Field(None, description="预处理块列表")
    para_blocks: Optional[List[Dict[str, Any]]] = Field(None, description="段落块列表")
    discarded_blocks: Optional[List[Dict[str, Any]]] = Field(None, description="丢弃块列表")
    note: Optional[str] = Field(None, description="备注")


class KnowledgeItemInfoQueryDTO(BaseModel):
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    master_id: Optional[str] = Field(None, description="主文档ID")
    page_idx: Optional[int] = Field(None, ge=0, description="页码索引")


class KnowledgeItemInfoDTO(BaseModel):
    id: Optional[PydanticObjectId] = None
    uid: str
    tenant_id: str
    master_id: str
    page_idx: int
    page_size: Dict[str, Any] = Field(default_factory=dict)
    preproc_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    para_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    discarded_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    note: Optional[str] = None
    created_at: str
    updated_at: str


class KnowledgeItemChunkCreateDTO(BaseModel):
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    master_id: str = Field(..., description="主文档ID")
    idx: int = Field(..., ge=0, description="块索引")
    chunk_type: ItemChunkTypeEnum = Field(..., description="块类型")
    text: Optional[str] = Field(None, description="文本内容")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_data: Optional[str] = Field(None, description="图片Base64数据")
    equation: Optional[str] = Field(None, description="公式内容")
    table_data: Optional[List[Dict]] = Field(None, description="表格数据")
    code_content: Optional[str] = Field(None, description="代码内容")
    code_language: Optional[str] = Field(None, description="编程语言")
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict, description="块元数据")
    position: Dict[str, float] = Field(default_factory=dict, description="位置信息")
    size: Dict[str, float] = Field(default_factory=dict, description="尺寸信息")
    vector_id: Optional[str] = Field(None, description="向量ID")


class KnowledgeItemChunkUpdateDTO(BaseModel):
    uid: Optional[str] = Field(None, description="UID")
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    master_id: Optional[str] = Field(None, description="主文档ID")
    idx: Optional[int] = Field(None, ge=0, description="块索引")
    chunk_type: Optional[ItemChunkTypeEnum] = Field(None, description="块类型")
    text: Optional[str] = Field(None, description="文本内容")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_data: Optional[str] = Field(None, description="图片Base64数据")
    equation: Optional[str] = Field(None, description="公式内容")
    table_data: Optional[List[Dict]] = Field(None, description="表格数据")
    code_content: Optional[str] = Field(None, description="代码内容")
    code_language: Optional[str] = Field(None, description="编程语言")
    chunk_metadata: Optional[Dict[str, Any]] = Field(None, description="块元数据")
    position: Optional[Dict[str, float]] = Field(None, description="位置信息")
    size: Optional[Dict[str, float]] = Field(None, description="尺寸信息")
    vector_id: Optional[str] = Field(None, description="向量ID")


class KnowledgeItemChunkQueryDTO(BaseModel):
    tenant_id: Optional[str] = Field(None, description="租户/组织ID")
    master_id: Optional[str] = Field(None, description="主文档ID")
    chunk_type: Optional[ItemChunkTypeEnum] = Field(None, description="块类型")
    idx: Optional[int] = Field(None, ge=0, description="块索引")


class KnowledgeItemChunkDTO(BaseModel):
    id: Optional[PydanticObjectId] = None
    uid: str
    tenant_id: str
    master_id: str
    idx: int
    chunk_type: ItemChunkTypeEnum
    text: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None
    equation: Optional[str] = None
    table_data: Optional[List[Dict]] = None
    code_content: Optional[str] = None
    code_language: Optional[str] = None
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=dict)
    size: Dict[str, float] = Field(default_factory=dict)
    vector_id: Optional[str] = None
    created_at: str
    updated_at: str


# 组合操作DTO
class KnowledgeItemWithInfosCreateDTO(BaseModel):
    item: KnowledgeItemCreateDTO = Field(..., description="知识条目数据")
    infos: List[KnowledgeItemInfoCreateDTO] = Field(default_factory=list, description="知识条目信息列表")


class KnowledgeItemChunkingDTO(BaseModel):
    item_id: PydanticObjectId = Field(..., description="知识条目ID")
    chunks: List[KnowledgeItemChunkCreateDTO] = Field(..., description="内容块列表")
    update_metadata: Optional[Dict[str, Any]] = Field(None, description="更新条目的元数据")


class KnowledgeItemWithDetailsQueryDTO(BaseModel):
    item_id: Optional[PydanticObjectId] = Field(None, description="知识条目ID")
    uid: Optional[str] = Field(None, description="知识条目UID")
    tenant_id: str = Field(..., description="租户ID")
    include_infos: bool = Field(False, description="是否包含详细信息")
    include_chunks: bool = Field(False, description="是否包含内容块")
    info_page_idx: Optional[int] = Field(None, description="指定页码的信息")
    chunk_types: Optional[List[ItemChunkTypeEnum]] = Field(None, description="过滤的块类型")


class BatchOperationResultDTO(BaseModel):
    success: bool
    message: Optional[str] = None
    total_count: int
    success_count: int
    failed_count: int
    failed_items: List[str] = Field(default_factory=list)