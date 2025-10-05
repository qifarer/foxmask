# -*- coding: utf-8 -*-
# foxmask/shared/dependencies.py
# Shared dependencies for FastAPI routes and services

from fastapi import Depends, Form, HTTPException, status, Header, Request, Security
from fastapi.security import HTTPBearer,APIKeyHeader, HTTPAuthorizationCredentials
from typing import Optional, Callable, List, Dict, Any
import time
from jose import JWTError, jwt

from foxmask.core.config import settings
from foxmask.core.logger import logger
from foxmask.auth.services import auth_service
from foxmask.utils.casdoor_client import casdoor_client

import json
from pydantic import ValidationError

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


# Casdoor 配置
CASDOOR_CONFIG = {
    "endpoint": settings.CASDOOR_ENDPOINT,
    "client_id": settings.CASDOOR_CLIENT_ID,
    "client_secret": settings.CASDOOR_CLIENT_SECRET,
    "certificate": settings.CASDOOR_CERT,
    "org_name": settings.CASDOOR_ORG_NAME,
    "application_name": settings.CASDOOR_APP_NAME,
}

# JWT 令牌验证
security = HTTPBearer()

async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """验证 JWT 令牌并返回解码后的声明"""
    try:
        # 使用 Casdoor 的公钥验证 JWT 签名
        payload = jwt.decode(
            credentials.credentials,
            CASDOOR_CONFIG["certificate"],
            algorithms=["RS256"],
            audience=CASDOOR_CONFIG["client_id"],
            options={"verify_aud": True}
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
async def get_user_from_token(
    token_payload: Dict[str, Any] = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """从 JWT 令牌中获取用户信息"""
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier",
        )
    
    
    # 可以从令牌中获取更多用户信息，或者调用 Casdoor API 获取完整用户信息
    return {
        "user_id": user_id,
        "username": token_payload.get("name"),
        "email": token_payload.get("email"),
        "permissions": token_payload.get("permissions", []),
        "roles": token_payload.get("roles", [])
    }


class GraphQLContext:
    """GraphQL上下文管理器"""
    
    def __init__(self, request, user_id: str = None, tenant_id: str = None):
        self.request = request
        self.user_id = user_id or "system"
        self.tenant_id = tenant_id or "default"
        self.ip_address = self._get_client_ip(request)
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        if hasattr(request, "headers"):
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                return x_forwarded_for.split(",")[0]
            return request.headers.get("X-Real-IP") or "unknown"
        return "unknown"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "ip_address": self.ip_address
        }


async def get_context1(request) -> dict:
    """获取GraphQL上下文"""
    # 这里应该实现真实的用户认证和租户识别逻辑
    # 目前使用模拟数据
    
    # 从请求头获取用户信息
    user_id = request.headers.get("X-User-ID", "system")
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    
    context = GraphQLContext(request, user_id, tenant_id)
    return context.to_dict()


async def get_context(
    token_payload: Dict[str, Any] = Depends(verify_jwt_token),
):
    return {
        "user_id": token_payload.get("sub"),
        "username": token_payload.get("name"),
        "email": token_payload.get("email"),
        "permissions": token_payload.get("permissions", []),
        "roles": token_payload.get("roles", []),
        "tenant_id": "foxmask",  # 示例静态租户ID,
        "tenantname": "foxmask"
    }

# API Key 验证（兼容旧版）
async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)
) -> str:
    """从请求头获取 API Key（兼容旧版）"""
    if not x_api_key:
        # 检查是否有 Bearer token
        authorization: str = Header(None)
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]  # 提取 Bearer token
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key or Bearer token is required",
            headers={"WWW-Authenticate": "APIKey, Bearer"},
        )
    return x_api_key

async def validate_api_key_access(
    request: Request,
    api_key: str = Depends(get_api_key_from_header),
    required_permission: Optional[str] = None,
    required_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """验证 API 访问权限，支持 API Key 和 JWT 令牌"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # 判断是 API Key 还是 JWT Token
        if api_key.startswith("eyJhbGciOi"):  # 简单的 JWT 令牌识别
            # JWT 令牌验证
            try:
                payload = jwt.decode(
                    api_key,
                    CASDOOR_CONFIG["certificate"],
                    algorithms=["RS256"],
                    audience=CASDOOR_CONFIG["client_id"],
                    options={"verify_aud": False}  # 不强制验证 audience，更灵活
                )
                
                user_permissions = payload.get("permissions", [])
                user_roles = payload.get("roles", [])
                
                # 检查权限
                if required_permission and required_permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required permission: {required_permission}"
                    )
                
                # 检查角色
                if required_roles and not any(role in user_roles for role in required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {required_roles}"
                    )
                
                # 速率限制（基于用户ID）
                user_id = payload.get("sub")
                if user_id and not await auth_service.check_rate_limit(user_id, "minute"):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                    )
                
                processing_time = time.time() - start_time
                
                # 记录使用情况
                await auth_service.log_api_usage(
                    user_id=user_id,
                    endpoint=request.url.path,
                    method=request.method,
                    ip_address=client_ip,
                    response_status=200,
                    processing_time=processing_time,
                    user_agent=request.headers.get("user-agent"),
                    auth_method="jwt"
                )
                
                return {
                    "user_id": user_id,
                    "username": payload.get("name"),
                    "permissions": user_permissions,
                    "roles": user_roles,
                    "auth_method": "jwt"
                }
                
            except JWTError as e:
                logger.warning(f"JWT validation failed: {e}")
                # 如果不是 JWT，继续尝试作为 API Key 验证
        
        # API Key 验证（传统方式）
        api_key_record = await auth_service.validate_api_key(
            api_key, required_permission, client_ip, request.headers.get("origin")
        )
        
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key or insufficient permissions",
            )
        
        # 检查速率限制
        if not await auth_service.check_rate_limit(str(api_key_record.id), "minute"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
        
        processing_time = time.time() - start_time
        
        # 记录使用情况
        await auth_service.log_api_usage(
            api_key_id=str(api_key_record.id),
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            response_status=200,
            processing_time=processing_time,
            user_agent=request.headers.get("user-agent"),
            auth_method="api_key"
        )
        
        return {
            "api_key_id": str(api_key_record.id),
            "user_id": api_key_record.casdoor_user_id,
            "permissions": api_key_record.permissions,
            "client_ip": client_ip,
            "auth_method": "api_key"
        }
        
    except HTTPException as he:
        processing_time = time.time() - start_time
        await auth_service.log_api_usage(
            user_id="unknown",
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            response_status=he.status_code,
            processing_time=processing_time,
            user_agent=request.headers.get("user-agent"),
            auth_method="unknown",
            error_detail=he.detail
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error during auth validation: {e}")
        processing_time = time.time() - start_time
        await auth_service.log_api_usage(
            user_id="unknown",
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            response_status=500,
            processing_time=processing_time,
            user_agent=request.headers.get("user-agent"),
            auth_method="unknown",
            error_detail=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error"
        )

# 权限验证装饰器
def require_permission(permission: str):
    """要求特定权限的依赖"""
    async def permission_dependency(
        auth_info: Dict[str, Any] = Depends(
            lambda request: validate_api_key_access(
                request, required_permission=permission
            )
        )
    ):
        return auth_info
    return permission_dependency

def require_any_permission(permissions: List[str]):
    """要求任意一个权限的依赖"""
    async def any_permission_dependency(
        auth_info: Dict[str, Any] = Depends(
            lambda request: validate_api_key_access(
                request, required_permission=None  # 在函数内部检查
            )
        )
    ):
        user_permissions = auth_info.get("permissions", [])
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required any of permissions: {permissions}"
            )
        return auth_info
    return any_permission_dependency

def require_role(role: str):
    """要求特定角色的依赖"""
    async def role_dependency(
        auth_info: Dict[str, Any] = Depends(
            lambda request: validate_api_key_access(
                request, required_roles=[role]
            )
        )
    ):
        return auth_info
    return require_role

# 快捷权限依赖
require_read = require_permission("read")
require_write = require_permission("write")
require_delete = require_permission("delete")
require_admin = require_permission("admin")

# 快捷角色依赖
require_user_role = require_role("user")
require_admin_role = require_role("admin")
require_super_admin_role = require_role("super-admin")

async def get_api_context(auth_info: Dict[str, Any] = Depends(require_read)) -> Dict[str, Any]:
    """获取 API 上下文信息"""
    return {
        "user_id": auth_info.get("user_id") or auth_info.get("api_key_id"),
        "permissions": auth_info.get("permissions", []),
        "roles": auth_info.get("roles", []),
        "auth_method": auth_info.get("auth_method", "unknown")
    }

# 数据库依赖（保持不变）
async def get_mongo_db():
    """Get MongoDB database instance"""
    from foxmask.core.mongo import mongodb
    return mongodb.database

async def get_kafka_manager():
    """Get Kafka manager instance"""
    from foxmask.core.kafka import kafka_manager
    return kafka_manager

async def get_minio_client():
    """Get MinIO client instance"""
    from foxmask.utils.minio_client import minio_client
    return minio_client

async def get_weaviate_client():
    """Get Weaviate client instance"""
    from foxmask.utils.weaviate_client import weaviate_client
    return weaviate_client

async def get_neo4j_client():
    """Get Neo4j client instance"""
    from foxmask.utils.neo4j_client import neo4j_client
    return neo4j_client