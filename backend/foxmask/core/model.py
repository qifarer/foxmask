# -*- coding: utf-8 -*-
# foxmask/core/model.py
# Copyright (C) 2025 FoxMask Inc.
# author: Roky

from beanie import Document
from pydantic import Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from foxmask.utils.helpers import get_current_time


class Visibility(str, Enum):
    """
    知识可用性枚举
    定义知识的访问权限级别
    """
    PRIVATE = "private"      # 仅上传者可见
    TENANT = "tenant"        # 租户内所有用户可见
    PUBLIC = "public"        # 公开访问


class BaseModel(Document):
    """
    知识管理基础模型
    包含所有知识相关模型的共同属性和方法
    """
    # 基本信息
    title: str = Field(..., description="标题", max_length=200)
    description: Optional[str] = Field(None, description="描述", max_length=1000)
    
    # 分类与标签
    tags: List[str] = Field(default_factory=list, description="标签")
    category: Optional[str] = Field(None, description="分类")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")
    
    # 所有权与权限
    tenant_id: str = Field(..., description="租户/组织ID")
    visibility: Visibility = Field(
        Visibility.PRIVATE, 
        description="知识可用性级别"
    )
    allowed_users: List[str] = Field(
        default_factory=list, 
        description="有访问权限的用户ID列表"
    )
    allowed_roles: List[str] = Field(
        default_factory=list, 
        description="有访问权限的角色列表"
    )
    
    # 时间信息
    created_at: datetime = Field(
        default_factory=get_current_time, 
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=get_current_time, 
        description="更新时间"
    )
    created_by: str = Field(..., description="创建者用户ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "示例标题",
                "description": "示例描述",
                "tags": ["tag1", "tag2"],
                "category": "示例分类",
                "metadata": {"key": "value"},
                "tenant_id": "tenant_123",
                "visibility": "private",
                "allowed_users": ["user1", "user2"],
                "allowed_roles": ["admin", "editor"],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": "user123"
            }
        }
    )
    
    class Settings:
        """基础索引配置"""
        indexes = [
            IndexModel([("tenant_id", ASCENDING)]),
            IndexModel([("visibility", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
            IndexModel([("allowed_users", ASCENDING)]),
            IndexModel([("allowed_roles", ASCENDING)]),
            IndexModel([("title", TEXT), ("description", TEXT)]),
        ]
    
    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = get_current_time()
    
    def set_error_info(self, error_type: str, error_message: str, details: Optional[Dict] = None):
        """设置错误信息"""
        self.error_info = {
            "error_type": error_type,
            "error_message": error_message,
            "error_details": details or {},
            "occurred_at": get_current_time()
        }
        self.update_timestamp()
    
    def clear_error_info(self):
        """清除错误信息"""
        self.error_info = None
        self.update_timestamp()
    
    def add_allowed_user(self, user_id: str):
        """添加允许访问的用户"""
        if user_id not in self.allowed_users:
            self.allowed_users.append(user_id)
            self.update_timestamp()
    
    def remove_allowed_user(self, user_id: str):
        """移除允许访问的用户"""
        if user_id in self.allowed_users:
            self.allowed_users.remove(user_id)
            self.update_timestamp()
    
    def add_allowed_role(self, role: str):
        """添加允许访问的角色"""
        if role not in self.allowed_roles:
            self.allowed_roles.append(role)
            self.update_timestamp()
    
    def remove_allowed_role(self, role: str):
        """移除允许访问的角色"""
        if role in self.allowed_roles:
            self.allowed_roles.remove(role)
            self.update_timestamp()
    
    def change_visibility(self, visibility: Visibility):
        """更改可见性设置"""
        self.visibility = visibility
        self.update_timestamp()
    
    def has_access(self, user_id: str, user_roles: List[str]) -> bool:
        """检查用户是否有访问权限"""
        if self.visibility == Visibility.PUBLIC:
            return True
        
        if self.visibility == Visibility.TENANT:
            # 租户内所有用户都有访问权限
            return True
        
        if self.visibility == Visibility.PRIVATE:
            # 私有权限检查
            if user_id == self.created_by:
                return True
            if user_id in self.allowed_users:
                return True
            if any(role in user_roles for role in self.allowed_roles):
                return True
        
        return False
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()
    
    def remove_tag(self, tag: str):
        """移除标签"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_timestamp()
    
    def update_metadata(self, key: str, value: Any):
        """更新元数据"""
        self.metadata[key] = value
        self.update_timestamp()
