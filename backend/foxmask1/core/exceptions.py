# foxmask/core/exceptions.py
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

class BaseServiceError(Exception):
    """基础服务异常"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class AuthenticationError(BaseServiceError):
    """认证异常"""
    def __init__(self, message: str = "认证失败", status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(message, status_code)

class AuthorizationError(BaseServiceError):
    """授权异常"""
    def __init__(self, message: str = "权限不足", status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(message, status_code)

class NotFoundError(BaseServiceError):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到", status_code: int = status.HTTP_404_NOT_FOUND):
        super().__init__(message, status_code)

class ValidationError(BaseServiceError):
    """验证异常"""
    def __init__(self, message: str = "验证失败", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message, status_code)

class ServiceError(BaseServiceError):
    """服务异常"""
    def __init__(self, message: str = "服务错误", status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message, status_code)

class RateLimitError(BaseServiceError):
    """限流异常"""
    def __init__(self, message: str = "请求过于频繁", status_code: int = status.HTTP_429_TOO_MANY_REQUESTS):
        super().__init__(message, status_code)

# 自定义异常处理器
async def custom_exception_handler(request, exc: BaseServiceError):
    """自定义异常处理器"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": str(exc),
            "status_code": exc.status_code
        }
    )

# 注册异常处理器
exception_handlers = {
    AuthenticationError: custom_exception_handler,
    AuthorizationError: custom_exception_handler,
    NotFoundError: custom_exception_handler,
    ValidationError: custom_exception_handler,
    ServiceError: custom_exception_handler,
    RateLimitError: custom_exception_handler,
}