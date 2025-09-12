from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from typing import Callable, Optional
import uuid

from ..logger import logger, request_id_var, user_id_var, correlation_id_var, RequestContext
from ..exceptions import FoxmaskException
from ..config import settings  # 添加导入 settings

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request IDs
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Try to get user ID from auth (if available)
        user_id = ""
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)
        
        # Set context for logging
        with RequestContext(request_id, user_id, correlation_id):
            start_time = time.time()
            
            try:
                # Add request IDs to response headers
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Correlation-ID"] = correlation_id
                
                # Log request completion
                duration = (time.time() - start_time) * 1000
                logger.performance(
                    f"{request.method} {request.url.path}",
                    duration,
                    {
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "http_status": response.status_code,
                        "http_query": dict(request.query_params),
                        "client_ip": request.client.host if request.client else "unknown",
                        "user_agent": request.headers.get("user-agent", ""),
                    }
                )
                
                return response
                
            except FoxmaskException as e:
                # Handle known application exceptions
                duration = (time.time() - start_time) * 1000
                logger.error(
                    f"Application error: {e.error_code}",
                    {
                        "error_code": e.error_code,
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "http_status": e.status_code,
                        "duration_ms": duration,
                        "client_ip": request.client.host if request.client else "unknown",
                    },
                    exc_info=e
                )
                
                return JSONResponse(
                    status_code=e.status_code,
                    content=e.to_dict(),
                    headers={
                        "X-Request-ID": request_id,
                        "X-Correlation-ID": correlation_id,
                        **e.headers
                    }
                )
                
            except Exception as e:
                # Handle unexpected exceptions
                duration = (time.time() - start_time) * 1000
                logger.error(
                    "Unexpected server error",
                    {
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "http_status": 500,
                        "duration_ms": duration,
                        "client_ip": request.client.host if request.client else "unknown",
                    },
                    exc_info=e
                )
                
                # Don't expose internal details in production
                if settings.DEBUG:  # 现在 settings 已经导入了
                    detail = f"Unexpected error: {str(e)}"
                else:
                    detail = "Internal server error"
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error_code": "INTERNAL_SERVER_ERROR",
                        "detail": detail,
                        "context": {"request_id": request_id}
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "X-Correlation-ID": correlation_id
                    }
                )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean up old entries
        self.requests = {
            ip: data for ip, data in self.requests.items()
            if current_time - data["last_reset"] < self.window
        }
        
        if client_ip not in self.requests:
            self.requests[client_ip] = {
                "count": 1,
                "last_reset": current_time  # 正确设置 last_reset
            }
        else:
            self.requests[client_ip]["count"] += 1
        
        if self.requests[client_ip]["count"] > self.max_requests:
            from ..exceptions import RateLimitError
            raise RateLimitError(self.max_requests, f"{self.window}s")
        
        return await call_next(request)