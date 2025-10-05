# foxmask/knowledge/models/knowledge_base.py
from foxmask.core.model import MasterBaseModel
from pydantic import Field
from typing import Dict, Any, List
from enum import Enum 
from pymongo import IndexModel, ASCENDING, DESCENDING

class KnowledgeBaseStatusEnum(str, Enum):
    DRAFT = "draft"          # 草稿状态，
    ACTIVE = "active"        # 活跃
    ARCHIVE = "archive"      # 归档
   
class KnowledgeBase(MasterBaseModel):
    """知识库模型"""
    items: List[Dict[str, Any]] = Field(default_factory=dict, description="知识条目数据，按类型组织")
       
    class Settings:
        name = "knowledge_bases"
        indexes = [
            IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("item_type", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
        ]