# foxmask/core/types.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Generic, TypeVar, Optional, Any, List
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

T = TypeVar('T')

class EntityID(UUID):
    """实体ID类型"""
    @classmethod
    def generate(cls) -> 'EntityID':
        return cls(str(uuid4()))
    
    def __str__(self):
        return str(self)

class ISOTimestamp(str):
    """ISO时间戳类型"""
    @classmethod
    def now(cls) -> 'ISOTimestamp':
        from datetime import datetime, timezone
        return cls(datetime.now(timezone.utc).isoformat())

class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    items: List[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 100
    has_next: bool = False

class BaseResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    error_code: Optional[str] = None

class QueryParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(100, ge=1, le=1000)
    sort_by: Optional[str] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")