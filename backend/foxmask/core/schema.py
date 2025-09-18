
import strawberry
from enum import Enum

# 使用装饰器方式
@strawberry.enum
class VisibilityEnum(Enum):
    """可见性枚举"""
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"