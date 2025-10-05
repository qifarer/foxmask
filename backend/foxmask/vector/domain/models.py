from foxmask.core.model import MasterBaseModel, SlaveBaseModel
from pydantic import Field
from typing import Dict, Any, Optional, List
from enum import Enum
from pymongo import IndexModel, ASCENDING, DESCENDING


class KnowledgeItemTypeEnum(str, Enum):
    FILE = "file"
    WEBPAGE = "webpage"
    API = "api"
    CHAT = "chat"
    PRODUCT = "product"
    BRAND = "brand"
    CUSTOM = "custom"


class ItemChunkTypeEnum(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    EQUATION = "equation"


class KnowledgeItem(MasterBaseModel):
    item_type: KnowledgeItemTypeEnum = Field(..., description="知识条目类型")
    source_id: Optional[str] = Field(None, description="源ID")
    
    class Settings:
        name = "knowledge_items"
        indexes = [
            IndexModel([("tenant_id", ASCENDING), ("item_type", ASCENDING)]),
            IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("item_type", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
        ]


class KnowledgeItemInfo(SlaveBaseModel):
    page_idx: int = Field(..., ge=0, description="页码索引")
    page_size: Dict[str, Any] = Field(default_factory=dict, description="页面尺寸信息")
    preproc_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="预处理块列表")
    para_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="段落块列表")
    discarded_blocks: List[Dict[str, Any]] = Field(default_factory=list, description="丢弃块列表")
    
    class Settings:
        name = "knowledge_item_infos"
        indexes = [
            IndexModel([("tenant_id", ASCENDING), ("master_id", ASCENDING)]),
            IndexModel([("master_id", ASCENDING), ("page_idx", ASCENDING)], unique=True),
            IndexModel([("master_id", ASCENDING)]),
        ]


class KnowledgeItemChunk(SlaveBaseModel):
    chunk_idx: int = Field(..., ge=0, description="块索引")
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
   
    class Settings:
        name = "knowledge_item_chunks"
        indexes = [
            IndexModel([("tenant_id", ASCENDING), ("master_id", ASCENDING)]),
            IndexModel([("master_id", ASCENDING), ("idx", ASCENDING)], unique=True),
            IndexModel([("chunk_type", ASCENDING)]),
            IndexModel([("master_id", ASCENDING), ("chunk_type", ASCENDING)]),
        ]