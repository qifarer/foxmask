import strawberry
from enum import Enum
from typing import Optional, List, Generic, TypeVar
from strawberry.relay import Node, Connection, PageInfo as RelayPageInfo
from strawberry.scalars import JSON
from datetime import datetime

T = TypeVar("T")

# 使用装饰器方式
@strawberry.enum
class VisibilityEnum(Enum):
    """可见性枚举"""
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"

@strawberry.enum
class StatusEnum(Enum):
    """状态枚举"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"  


# 修复 BaseResponse 和其他核心类型
@strawberry.type
class BaseResponse:
    success: bool
    errors: Optional[List["Error"]] = None

@strawberry.type
class Error:
    message: str
    code: str
    field: Optional[str] = None

# 修复 User 类型中的可变默认值问题
@strawberry.type
class User:
    id: str
    username: str
    email: str
    roles: List[str] = strawberry.field(default_factory=list)  # 修复这里
    permissions: List[str] = strawberry.field(default_factory=list)  # 修复这里
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


# 分页相关类型
@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int] = None
    current_page: int = 1
    total_pages: Optional[int] = None

