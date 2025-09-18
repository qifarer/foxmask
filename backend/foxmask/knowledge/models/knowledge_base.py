# foxmask/knowledge/models/knowledge_base.py
from foxmask.core.model import BaseModel
from pydantic import Field
from typing import Dict, Any, List
from enum import Enum 
from pymongo import IndexModel, ASCENDING, DESCENDING

class KnowledgeBaseStatusEnum(str, Enum):
    DRAFT = "draft"          # 草稿状态，
    ACTIVE = "active"        # 活跃
    ARCHIVE = "archive"      # 归档
   
class KnowledgeBase(BaseModel):
    """知识库模型"""
    items: Dict[str, Any] = Field(default_factory=dict, description="知识条目数据，按类型组织")
    item_count: int = Field(0, description="知识条目总数")
    status: KnowledgeBaseStatusEnum = Field(
        KnowledgeBaseStatusEnum.DRAFT, 
        description="状态"
    )
    class Settings:
        name = "knowledge_bases"
        indexes = BaseModel.Settings.indexes + [
            IndexModel([("item_count", DESCENDING)]),
            IndexModel([("category", ASCENDING)]),
        ]