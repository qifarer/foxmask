# foxmask/knowledge/models/knowledge_item.py
from foxmask.core.model import BaseModel
from pydantic import Field
from typing import  Dict, Any, Optional
from enum import Enum
from pymongo import IndexModel, ASCENDING

class KnowledgeItemStatusEnum(str, Enum):
    PENDING = "pending"
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VECTORIZING = "vectorizing"
    VECTORIZED = "vectorized"
    GRAPHING = "graphing"
    COMPLETED = "completed"
    FAILED = "failed"

class KnowledgeItemTypeEnum(str, Enum):
    FILE = "file"
    WEBPAGE = "webpage"
    API = "api"
    CHAT = "chat"
    PRODUCT = "product"
    BRAND = "brand"
    CUSTOM = "custom"

class ItemContentTypeEnum(str, Enum):
    SOURCE = "source"
    PARSED = "parsed"
    VECTOR = "vector"
    GRAPH = "graph"

class KnowledgeItemContent(BaseModel):
    """知识条目内容模型"""
    item_id: str = Field(..., description="关联的知识条目ID")
    content_type: ItemContentTypeEnum = Field(..., description="内容类型")
    content_data: Dict[str, Any] = Field(default_factory=dict, description="内容元数据")
    # 处理状态信息
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="处理过程元数据"
    )
    error_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="错误信息"
    )
    # 版本控制
    version: int = Field(1, description="内容版本")
    is_latest: bool = Field(True, description="是否为最新版本")

    class Settings:
        name = "knowledge_item_contents"
        indexes = BaseModel.Settings.indexes + [
            IndexModel([("item_id", ASCENDING), ("content_type", ASCENDING)]),
            IndexModel([("item_id", ASCENDING), ("content_type", ASCENDING), ("is_latest", ASCENDING)]),
            IndexModel([("content_type", ASCENDING)]),
        ]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeItemContent':
        """从字典创建User实例"""
        return cls(**data)
    
    @classmethod
    def to_dict(self, exclude_none: bool = True, **kwargs) -> Dict[str, Any]:
        """将User实例转换为字典"""
        return self.model_dump(exclude_none=exclude_none, **kwargs)

class KnowledgeItem(BaseModel):
    """知识条目模型"""
    item_type: KnowledgeItemTypeEnum = Field(..., description="知识条目类型")
    status: KnowledgeItemStatusEnum = Field(KnowledgeItemStatusEnum.CREATED, description="处理状态")
    content: Dict[str, Any] = Field(default_factory=dict, description="内容数据")
    # 处理状态信息
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="处理过程元数据"
    )
    error_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="错误信息"
    )
    class Settings:
        name = "knowledge_items"
        indexes = BaseModel.Settings.indexes + [
            IndexModel([("item_type", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("item_type", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeItem':
        """从字典创建User实例"""
        return cls(**data)
    
    @classmethod
    def to_dict(self, exclude_none: bool = True, **kwargs) -> Dict[str, Any]:
        """将User实例转换为字典"""
        return self.model_dump(exclude_none=exclude_none, **kwargs)
    