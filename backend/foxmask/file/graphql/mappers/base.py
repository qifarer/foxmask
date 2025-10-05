# mappers/base.py
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from datetime import datetime
import json
import strawberry
from strawberry.scalars import JSON

T = TypeVar('T')
DTO = TypeVar('DTO')
Schema = TypeVar('Schema')

class BaseMapper:
    """映射器基类"""
    
    @staticmethod
    def safe_enum_conversion(value: Any, enum_class: Type) -> Any:
        """安全枚举转换"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                return enum_class(value)
            elif hasattr(value, 'value'):
                return enum_class(value.value)
            else:
                return enum_class(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def safe_list_conversion(items: Optional[List], converter: callable) -> List:
        """安全列表转换"""
        if not items:
            return []
        return [converter(item) for item in items if item is not None]
    
    @staticmethod
    def safe_datetime_conversion(value: Any) -> Optional[datetime]:
        """安全日期时间转换"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return None
        return None
    
    @staticmethod
    def safe_json_conversion(value: Any) -> Optional[JSON]:
        """安全 JSON 转换"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return None
        return value