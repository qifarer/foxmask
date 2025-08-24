# foxmask/core/tracking.py
import time
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid
from functools import wraps
from foxmask.core.database import get_database
from foxmask.core.config import get_settings
from foxmask.auth.schemas import User

settings = get_settings()

class EventType(str, Enum):
    """审计事件类型"""
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_DELETE = "document_delete"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    API_CALL = "api_call"
    SYSTEM_EVENT = "system_event"

class EventLevel(str, Enum):
    """事件级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditEvent(BaseModel):
    """审计事件模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    event_level: EventLevel = EventLevel.INFO
    user_id: Optional[str] = None
    username: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TrackingService:
    """数据跟踪服务"""
    
    def __init__(self):
        self.db = get_database()
    
    async def log_event(self, event: AuditEvent):
        if not self.db:
            # 可以打个 warning 日志，而不是直接报错
            # logger.warning("TrackingService DB not initialized, skipping audit log.")
            return
        await self.db.audit_events.insert_one(event.dict())
        
    async def log_api_call(
        self,
        method: str,
        endpoint: str,
        user: Optional[User] = None,
        status_code: int = 200,
        duration_ms: int = 0,
        parameters: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录API调用"""
        event = AuditEvent(
            event_type=EventType.API_CALL,
            event_level=EventLevel.INFO,
            user_id=user.id if user else None,
            username=user.username if user else None,
            resource_type="api",
            resource_id=endpoint,
            action=f"{method} {endpoint}",
            details={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "parameters": parameters or {},
                "duration_ms": duration_ms
            },
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            success=status_code < 400
        )
        await self.log_event(event)
    
    async def log_file_operation(
        self,
        operation: str,
        file_id: str,
        filename: str,
        user: User,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录文件操作"""
        event_type = {
            "upload": EventType.FILE_UPLOAD,
            "download": EventType.FILE_DOWNLOAD,
            "delete": EventType.FILE_DELETE
        }.get(operation, EventType.FILE_UPLOAD)
        
        event = AuditEvent(
            event_type=event_type,
            user_id=user.id,
            username=user.username,
            resource_type="file",
            resource_id=file_id,
            action=operation,
            details={
                "filename": filename,
                "file_id": file_id,
                **(details or {})
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
        await self.log_event(event)
    
    async def log_document_operation(
        self,
        operation: str,
        document_id: str,
        title: str,
        user: User,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录文档操作"""
        event_type = {
            "create": EventType.DOCUMENT_CREATE,
            "update": EventType.DOCUMENT_UPDATE,
            "delete": EventType.DOCUMENT_DELETE
        }.get(operation, EventType.DOCUMENT_CREATE)
        
        event = AuditEvent(
            event_type=event_type,
            user_id=user.id,
            username=user.username,
            resource_type="document",
            resource_id=document_id,
            action=operation,
            details={
                "title": title,
                "document_id": document_id,
                **(details or {})
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=success
        )
        await self.log_event(event)
    
    async def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[AuditEvent]:
        """查询审计事件"""
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        
        if event_type:
            query["event_type"] = event_type
        
        if resource_type:
            query["resource_type"] = resource_type
        
        if resource_id:
            query["resource_id"] = resource_id
        
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        cursor = self.db.audit_events.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return [AuditEvent(**doc) async for doc in cursor]
    
    async def get_user_activity_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动统计"""
        from datetime import timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": start_time, "$lte": end_time}
                }
            },
            {
                "$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1},
                    "last_event": {"$max": "$timestamp"}
                }
            }
        ]
        
        results = await self.db.audit_events.aggregate(pipeline).to_list(None)
        
        return {
            "user_id": user_id,
            "period": f"last_{days}_days",
            "start_time": start_time,
            "end_time": end_time,
            "events_by_type": {result["_id"]: result["count"] for result in results},
            "total_events": sum(result["count"] for result in results)
        }

# 全局跟踪服务实例
tracking_service = TrackingService()

# 性能监控装饰器
def track_performance(event_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 提取用户信息（如果存在）
                user = None
                for arg in args:
                    if hasattr(arg, 'id') and hasattr(arg, 'username'):
                        user = arg
                        break
                
                if not user:
                    for key, value in kwargs.items():
                        if hasattr(value, 'id') and hasattr(value, 'username'):
                            user = value
                            break
                
                # 记录性能事件
                await tracking_service.log_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_EVENT,
                        event_level=EventLevel.INFO,
                        user_id=user.id if user else None,
                        username=user.username if user else None,
                        action=event_name,
                        details={
                            "function": func.__name__,
                            "duration_ms": duration_ms,
                            "module": func.__module__
                        },
                        duration_ms=duration_ms,
                        success=True
                    )
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 记录错误事件
                await tracking_service.log_event(
                    AuditEvent(
                        event_type=EventType.SYSTEM_EVENT,
                        event_level=EventLevel.ERROR,
                        action=event_name,
                        details={
                            "function": func.__name__,
                            "duration_ms": duration_ms,
                            "module": func.__module__,
                            "error": str(e)
                        },
                        duration_ms=duration_ms,
                        success=False,
                        error_message=str(e)
                    )
                )
                
                raise
        
        return wrapper
    return decorator