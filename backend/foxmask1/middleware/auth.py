# foxmask/middleware/auth.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from foxmask.core.casdoor_auth import verify_casdoor_token, get_casdoor_user
from foxmask.core.exceptions import AuthenticationError
from foxmask.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", 
            "/health", "/info", "/",
            "/auth/login", "/auth/callback", "/auth/logout",
            "/.well-known/openid-configuration",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # 检查是否在排除路径中
        if self._should_exclude_request(request):
            return await call_next(request)
        
        # 检查GraphQL路径
        if request.url.path.startswith("/graphql"):
            # GraphQL认证在resolver中处理
            return await call_next(request)
        
        # 尝试从多个位置获取token
        token = self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization token missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # 验证Casdoor令牌
            is_valid, payload = await verify_casdoor_token(token)
            if not is_valid:
                logger.warning(f"Invalid token from {request.client.host if request.client else 'unknown'}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 获取用户信息
            user_info = await get_casdoor_user(token)
            if not user_info:
                logger.warning(f"User not found for valid token from {request.client.host if request.client else 'unknown'}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 将用户信息添加到请求状态
            request.state.user = user_info
            request.state.token = token
            request.state.user_id = user_info.get("sub", user_info.get("id", ""))
            request.state.user_name = user_info.get("name", user_info.get("preferred_username", ""))
            request.state.user_roles = user_info.get("roles", [])
            request.state.tenant_id = user_info.get("tenant_id", user_info.get("organization", ""))
            
            # 记录认证成功
            logger.info(f"User {request.state.user_name} authenticated successfully from {request.client.host if request.client else 'unknown'}")
            
            # 继续处理请求
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authentication error",
            )
    
    def _should_exclude_request(self, request: Request) -> bool:
        """检查请求是否应该排除认证"""
        # 检查精确路径匹配
        if request.url.path in self.exclude_paths:
            return True
        
        # 检查路径前缀
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return True
        
        # 检查OPTIONS方法（CORS预检请求）
        if request.method == "OPTIONS":
            return True
        
        # 检查静态文件路径
        if request.url.path.startswith("/static/") or request.url.path.startswith("/assets/"):
            return True
        
        return False
    
    def _extract_token(self, request: Request) -> str:
        """从请求中提取token"""
        # 1. 从Authorization头获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除 "Bearer " 前缀
        
        # 2. 从查询参数获取（用于WebSocket等）
        token = request.query_params.get("token")
        if token:
            return token
        
        # 3. 从cookie获取
        token = request.cookies.get(settings.CASDOOR_TOKEN_COOKIE_NAME or "casdoor_token")
        if token:
            return token
        
        # 4. 从X-Access-Token头获取
        token = request.headers.get("X-Access-Token")
        if token:
            return token
        
        return None

