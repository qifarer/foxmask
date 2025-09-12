# foxmask/core/casdoor_auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer, HTTPBearer, HTTPAuthorizationCredentials
from casdoor import CasdoorSDK
from foxmask.core.config import get_settings
from foxmask.core.exceptions import AuthenticationError
import aiohttp
import jwt
import logging
from typing import Tuple, Optional, Dict, Any, List

logger = logging.getLogger(__name__)
settings = get_settings()

# 初始化 Casdoor SDK (适配 casdoor==1.38.0)
casdoor_sdk = CasdoorSDK(
    endpoint=settings.CASDOOR_ENDPOINT,
    client_id=settings.CASDOOR_CLIENT_ID,
    client_secret=settings.CASDOOR_CLIENT_SECRET,
    certificate=settings.CASDOOR_CERT,   # 1.x 用 certificate
    org_name=settings.CASDOOR_ORG,       # 1.x 用 org_name
    application_name=settings.CASDOOR_APP,
)

# OAuth2 配置
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.CASDOOR_ENDPOINT}/login/oauth/authorize",
    tokenUrl=f"{settings.CASDOOR_ENDPOINT}/api/login/oauth/access_token",
)

# Bearer token 认证
security = HTTPBearer()
async def get_current_user() -> Dict[str, Any]:
    return {"id": "foxmask", "name": "foxmask", "email": "foxmask"}  # TODO: 临时占位
 
async def get_current_user1(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    return {"id": "get_current_user", "name": "", "email": ""}  # TODO: 临时占位
    """
    获取当前认证用户（基于Bearer token）
    """
    try:
        if not credentials or not credentials.scheme == "Bearer":
            raise AuthenticationError(
                "Invalid authentication scheme",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        token = credentials.credentials
        if not token:
            raise AuthenticationError(
                "Token is missing",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        # 首先尝试使用 Casdoor SDK 解析 token
        try:
            user = casdoor_sdk.parse_jwt_token(token)
            if user:
                return _format_user_info(user)
        except Exception as sdk_error:
            logger.debug(f"Casdoor SDK token parsing failed, trying manual verification: {sdk_error}")
        
        # 如果 SDK 失败，尝试手动验证
        is_valid, payload = await verify_casdoor_token(token)
        '''
        if not is_valid or not payload:
            raise AuthenticationError(
                "Could not validate credentials",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        '''
        # 从 payload 或 API 获取用户信息
        user_info = await get_casdoor_user(token)
        if not user_info:
            # 如果 API 调用失败，使用 payload 中的信息
            user_info = _extract_user_from_payload(payload)
        
        return user_info
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise AuthenticationError(
            "Authentication failed",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取当前活跃用户（需要用户处于激活状态）
    """
    if not current_user.get("is_active", True):
        raise AuthenticationError(
            "User is inactive", 
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    return current_user

async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    获取管理员用户（需要管理员权限）
    """
    user_roles = current_user.get("roles", [])
    admin_roles = ["admin", "administrator", "superadmin", "system-admin"]
    
    if not any(role in user_roles for role in admin_roles):
        raise AuthenticationError(
            "Admin privileges required", 
            status_code=status.HTTP_403_FORBIDDEN
        )
    return current_user

async def require_role(role: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    检查用户是否具有特定角色
    """
    if role not in user.get("roles", []):
        raise AuthenticationError(
            f"Require {role} role to access this resource",
            status_code=status.HTTP_403_FORBIDDEN
        )
    return user

async def require_permission(permission: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    检查用户是否具有特定权限
    """
    user_permissions = user.get("permissions", [])
    if permission not in user_permissions:
        raise AuthenticationError(
            f"Require {permission} permission to access this resource",
            status_code=status.HTTP_403_FORBIDDEN
        )
    return user

# -------------------------
# JWT 验证工具函数
# -------------------------

async def verify_casdoor_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    验证 Casdoor JWT 令牌
    """
    try:
        public_key = await _get_casdoor_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256", "HS256"],
            audience=settings.CASDOOR_CLIENT_ID,
            issuer=settings.CASDOOR_ENDPOINT,  # 使用 endpoint 作为 issuer
            options={"verify_aud": True, "verify_iss": True}
        )
        return True, payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return False, None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return False, None

async def get_casdoor_user(token: str) -> Optional[Dict[str, Any]]:
    """
    从 Casdoor 获取用户信息
    """
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(
                f"{settings.CASDOOR_ENDPOINT}/api/userinfo",
                headers=headers
            ) as response:
                if response.status == 200:
                    user_info = await response.json()
                    return _format_user_info(user_info)
                logger.error(f"Failed to get user info: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None

async def _get_casdoor_public_key() -> str:
    """
    获取 Casdoor 公钥 (通过 OIDC JWKS 或配置)
    """
    # 首先尝试使用配置的证书
    if settings.CASDOOR_CERT:
        return settings.CASDOOR_CERT
    
    # 如果没有配置证书，尝试从 JWKS 获取
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.CASDOOR_ENDPOINT}/.well-known/openid-configuration"
            ) as response:
                if response.status == 200:
                    config = await response.json()
                    jwks_uri = config.get("jwks_uri")
                    if jwks_uri:
                        async with session.get(jwks_uri) as jwks_response:
                            if jwks_response.status == 200:
                                jwks = await jwks_response.json()
                                return _parse_jwks(jwks)
        
        # 如果都失败，使用默认的证书格式
        return f"-----BEGIN CERTIFICATE-----\n{settings.CASDOOR_CERT}\n-----END CERTIFICATE-----"
    except Exception as e:
        logger.error(f"Error getting Casdoor public key: {e}")
        raise AuthenticationError("Failed to get public key for token verification")

def _parse_jwks(jwks: Dict[str, Any]) -> str:
    """
    解析 JWKS 获取公钥
    """
    if jwks.get("keys") and len(jwks["keys"]) > 0:
        key = jwks["keys"][0]
        if "x5c" in key and len(key["x5c"]) > 0:
            cert = f"-----BEGIN CERTIFICATE-----\n{key['x5c'][0]}\n-----END CERTIFICATE-----"
            return cert
        elif "n" in key and "e" in key:
            # 处理 RSA 公钥
            from jwt.algorithms import RSAAlgorithm
            rsa_key = RSAAlgorithm.from_jwk(key)
            return rsa_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
    
    raise AuthenticationError("No valid public key found in JWKS")

def _format_user_info(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化用户信息为统一格式
    """
    return {
        "id": user_data.get("sub") or user_data.get("id") or user_data.get("preferred_username"),
        "username": user_data.get("preferred_username", ""),
        "email": user_data.get("email", ""),
        "display_name": user_data.get("name", user_data.get("display_name", "")),
        "avatar": user_data.get("picture", user_data.get("avatar", "")),
        "is_active": user_data.get("email_verified", True),
        "roles": user_data.get("roles", []),
        "permissions": user_data.get("permissions", []),
        "casdoor_user_id": user_data.get("id"),
        "casdoor_org": user_data.get("owner", settings.CASDOOR_ORG),
        "tenant_id": user_data.get("tenant_id", user_data.get("owner", settings.CASDOOR_ORG))
    }

def _extract_user_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 JWT payload 中提取用户信息
    """
    return {
        "id": payload.get("sub", ""),
        "username": payload.get("preferred_username", payload.get("sub", "")),
        "email": payload.get("email", ""),
        "display_name": payload.get("name", ""),
        "is_active": payload.get("email_verified", True),
        "roles": payload.get("roles", []),
        "permissions": payload.get("permissions", []),
        "casdoor_org": payload.get("iss", "").split("//")[-1].split("/")[0] if payload.get("iss") else settings.CASDOOR_ORG
    }

# 兼容性函数
async def get_user_with_permission(
    permission: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    获取具有特定权限的用户
    """
    return await require_permission(permission, current_user)

# 可选：用于测试的模拟用户
async def get_mock_user() -> Dict[str, Any]:
    """获取模拟用户（仅用于开发和测试）"""
    if get_settings().ENVIRONMENT == "production":
        raise AuthenticationError("Mock user not allowed in production")
    
    return {
        "id": "mock-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar": "https://example.com/avatar.jpg",
        "is_active": True,
        "roles": ["user"],
        "permissions": ["read", "write"],
        "casdoor_user_id": "mock-casdoor-id",
        "casdoor_org": settings.CASDOOR_ORG,
        "tenant_id": f"tenant-{settings.CASDOOR_ORG}"
    }