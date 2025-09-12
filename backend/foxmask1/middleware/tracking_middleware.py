# foxmask/middleware/tracking_middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from foxmask.core.tracking import tracking_service, AuditEvent, EventType, EventLevel
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
            
            # 从请求头中提取用户信息，而不是直接调用 get_current_user
            user = None
            authorization = request.headers.get("Authorization")
            if authorization and authorization.startswith("Bearer "):
                token = authorization[7:]  # 去掉 "Bearer " 前缀
                try:
                    # 直接解码 token 获取用户信息
                    from jose import jwt
                    from foxmask.core.config import get_settings
                    settings = get_settings()
                    
                    payload = jwt.decode(
                        token,
                        settings.SECRET_KEY,
                        algorithms=["HS256"],
                        options={"verify_aud": False}
                    )
                    user_id = payload.get("sub")
                    username = payload.get("preferred_username", "")
                    
                    if user_id:
                        from foxmask.auth.schemas import User
                        user = User(id=user_id, username=username)
                except Exception:
                    # 如果 token 无效，忽略错误
                    pass
            
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
            
            raise e