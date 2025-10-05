# -*- coding: utf-8 -*-
# foxmask/core/model.py
from beanie import Document, before_event, Replace, Insert, Update
from pydantic import Field, ConfigDict, model_validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
from bson import ObjectId
from foxmask.utils.helpers import get_current_timestamp
from foxmask.core.enums import Visibility, Status

class MasterBaseModel(Document):
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    title: str = Field(..., description="标题", min_length=1, max_length=300)
    desc: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    note: Optional[str] = Field(None, description="备注")
    status: Status = Field(default=Status.DRAFT, description="记录状态")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="知识可用性级别")
    created_at: datetime = Field(default_factory=get_current_timestamp, description="创建时间 (UTC)")
    updated_at: datetime = Field(default_factory=get_current_timestamp, description="更新时间 (UTC)")
    archived_at: Optional[datetime] = Field(None, description="归档时间(ISO)")
    created_by: Optional[str] = Field(None, description="创建者用户ID")
    allowed_users: List[str] = Field(default_factory=list, description="有访问权限的用户ID列表")
    allowed_roles: List[str] = Field(default_factory=list, description="有访问权限的角色列表")
    proc_meta: Dict[str, Any] = Field(default_factory=dict, description="处理过程元数据")
    error_info: Optional[Dict[str, Any]] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义元数据")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        validate_assignment=True
    )

    class Settings:
        abstract = True
        use_state_management = True
        validate_on_save = True

    @before_event(Replace, Insert, Update)
    def auto_update_timestamp(self):
        self.updated_at = get_current_timestamp()

    def update_timestamp(self) -> None:
        self.updated_at = get_current_timestamp()


class SlaveBaseModel(Document):
    uid: str = Field(..., description="UID")
    tenant_id: str = Field(..., description="租户/组织ID")
    master_id: str = Field(..., description="主文档ID")
    note: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(default_factory=get_current_timestamp, description="创建时间 (UTC)")
    updated_at: datetime = Field(default_factory=get_current_timestamp, description="更新时间 (UTC)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        validate_assignment=True
    )

    class Settings:
        abstract = True
        use_state_management = True
        validate_on_save = True
    
    @before_event(Replace, Insert, Update)
    def auto_update_timestamp(self):
        self.updated_at = get_current_timestamp()

    def update_timestamp(self) -> None:
        self.updated_at = get_current_timestamp()