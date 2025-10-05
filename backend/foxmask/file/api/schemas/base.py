# -*- coding: utf-8 -*-
# foxmask/file/api/schemas/base.py
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')  # 定义泛型类型

class Error(BaseModel):
    message: str
    code: str
    field: Optional[str] = None

class BaseResponse(BaseModel):
    success: bool
    errors: Optional[List[Error]] = None

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

class ListResponse(BaseModel, Generic[T]):
    """通用列表响应，支持泛型"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class PageInfoSchema(BaseModel):
    """分页信息"""
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int] = Field(default=None, ge=0)
    current_page: int = Field(default=1, ge=1)
    total_pages: Optional[int] = Field(default=None, ge=0)