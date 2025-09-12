# foxmask/auth/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import httpx
from foxmask.core.config import get_settings
from foxmask.core.exceptions import AuthenticationError
from foxmask.auth.schemas import User
settings = get_settings()

security = HTTPBearer()

class CasdoorOAuth:
    def __init__(self):
        self.casdoor_domain = settings.CASDOOR_ENDPOINT.rstrip("/")
        self.client_id = settings.CASDOOR_CLIENT_ID
        self.client_secret = settings.CASDOOR_CLIENT_SECRET
        self.org_name = settings.CASDOOR_ORG
        self.app_name = settings.CASDOOR_APP

    async def get_user_info(self, token: str) -> Optional[dict]:
        """从Casdoor获取用户信息"""
        try:
            async with httpx.AsyncClient() as client:
                # 方式1: 使用Casdoor的API验证token
                response = await client.get(
                    f"{self.casdoor_domain}/api/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                
                # 方式2: 如果第一种方式失败，尝试使用OIDC配置
                oidc_config = await self.get_oidc_config()
                if oidc_config:
                    response = await client.get(
                        oidc_config["userinfo_endpoint"],
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    if response.status_code == 200:
                        return response.json()
                
                return None
                
        except Exception:
            return None

    async def get_oidc_config(self) -> Optional[dict]:
        """获取Casdoor的OIDC配置"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.casdoor_domain}/.well-known/openid-configuration"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        return None

    async def validate_token(self, token: str) -> Optional[User]:
        """验证token并返回用户信息"""
        user_info = await self.get_user_info(token)
        if not user_info:
            return None
        
        # 将Casdoor用户信息转换为我们的User模型
        return User(
            id=user_info.get("sub") or user_info.get("id") or user_info.get("preferred_username"),
            username=user_info.get("preferred_username", ""),
            email=user_info.get("email", ""),
            display_name=user_info.get("name", ""),
            avatar=user_info.get("picture", ""),
            is_active=user_info.get("email_verified", True),
            roles=user_info.get("roles", []),
            permissions=user_info.get("permissions", []),
            # Casdoor特定字段
            casdoor_user_id=user_info.get("id"),
            casdoor_org=user_info.get("owner", self.org_name)
        )

casdoor_oauth = CasdoorOAuth()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    获取当前认证用户（基于Casdoor）
    """
    if not credentials or not credentials.scheme == "Bearer":
        raise AuthenticationError(  # 使用自定义异常
            "Invalid authentication scheme",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    token = credentials.credentials
    if not token:
        raise AuthenticationError(
            "Token is missing",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    user = await casdoor_oauth.validate_token(token)
    if not user:
        raise AuthenticationError(
            "Could not validate credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户（需要用户处于激活状态）
    """
    if not current_user.is_active:
        raise AuthenticationError("User is inactive", status_code=status.HTTP_401_UNAUTHORIZED)
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取管理员用户（需要管理员权限）
    """
    if "admin" not in current_user.roles and "administrator" not in current_user.roles:
        raise AuthenticationError("Admin privileges required", status_code=status.HTTP_403_FORBIDDEN)
    return current_user

async def get_user_with_permission(
    permission: str,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取具有特定权限的用户
    """
    if permission not in current_user.permissions:
        raise AuthenticationError(f"Permission '{permission}' required", status_code=status.HTTP_403_FORBIDDEN)
    return current_user

# 可选：直接从请求中获取token的版本
async def get_current_user_from_request(request: Request) -> User:
    """
    从请求头中直接获取用户信息
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError(
            "Invalid authentication header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.replace("Bearer ", "")
    user = await casdoor_oauth.validate_token(token)
    if not user:
        raise AuthenticationError(
            "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# 可选：用于测试的模拟用户
async def get_mock_user() -> User:
    """获取模拟用户（仅用于开发和测试）"""
    if settings.ENVIRONMENT == "production":
        raise AuthenticationError("Mock user not allowed in production")
    
    return User(
        id="mock-user-123",
        username="testuser",
        email="test@example.com",
        display_name="Test User",
        is_active=True,
        roles=["user"],
        permissions=["read", "write"]
    )