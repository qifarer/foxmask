# app/middleware/tracking_middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from foxmask.core.tracking import tracking_service, EventLevel
from foxmask.auth.dependencies import get_current_user
from foxmask.core.exceptions import AuthenticationError

class TrackingMiddleware(BaseHTTPMiddleware):
    """API调用跟踪中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查和其他不需要跟踪的端点
        if request.url.path in ["/health", "/docs", "/redoc", "/graphql"]:
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 获取用户信息
            user = None
            try:
                user = await get_current_user(request)
            except AuthenticationError:
                pass  # 未认证用户
            
            # 记录API调用
            await tracking_service.log_api_call(
                method=request.method,
                endpoint=request.url.path,
                user=user,
                status_code=response.status_code,
                duration_ms=duration_ms,
                parameters=dict(request.query_params),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
            return response
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录错误
            await tracking_service.log_event(
                AuditEvent(
                    event_type=EventType.API_CALL,
                    event_level=EventLevel.ERROR,
                    action=f"{request.method} {request.url.path}",
                    details={
                        "method": request.method,
                        "endpoint": request.url.path,
                        "error": str(e),
                        "duration_ms": duration_ms
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    success=False,
                    error_message=str(e)
                )
            )
            
            raise

# 性能监控装饰器
def track_performance(event_name: str):
    """性能监控装饰器"""
    def decorator(func):
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