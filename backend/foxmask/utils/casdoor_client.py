# -*- coding: utf-8 -*-
# Casdoor client utilitys
from casdoor import AsyncCasdoorSDK
from foxmask.core.config import settings
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class CasdoorAPIClient:
    def __init__(self):
        self.sdk = AsyncCasdoorSDK(
            endpoint=str(settings.CASDOOR_ENDPOINT),
            client_id=settings.CASDOOR_CLIENT_ID,
            client_secret=settings.CASDOOR_CLIENT_SECRET,
            certificate=settings.CASDOOR_CERT,
            org_name=settings.CASDOOR_ORG_NAME,
            application_name=settings.CASDOOR_APP_NAME
        )
    
    async def verify_user_access(self, user_id: str, resource: str, action: str) -> bool:
        """验证用户对资源的访问权限"""
        try:
            # 获取用户权限
            user = await self.sdk.get_user(user_id)
            if not user:
                return False
            
            # 检查用户角色和权限
            user_permissions = getattr(user, 'permissions', [])
            user_roles = getattr(user, 'roles', [])
            
            # 构建权限字符串
            required_permission = f"{resource}:{action}"
            
            # 检查直接权限
            if required_permission in user_permissions:
                return True
            
            # 检查角色权限（需要实现角色权限查询）
            for role_name in user_roles:
                if await self.check_role_permission(role_name, required_permission):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying user access: {e}")
            return False
    
    async def check_role_permission(self, role_name: str, permission: str) -> bool:
        """检查角色权限"""
        try:
            role = await self.sdk.get_role(role_name)
            if role and hasattr(role, 'permissions'):
                return permission in role.permissions
            return False
        except Exception as e:
            logger.error(f"Error checking role permission: {e}")
            return False
    
    async def get_user_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户有权访问的应用"""
        try:
            user = await self.sdk.get_user(user_id)
            if not user:
                return []
            
            # 这里需要根据Casdoor的实际API来获取用户应用
            # 简化实现：返回用户所属组织的应用
            applications = await self.sdk.get_applications()
            return [app for app in applications if hasattr(app, 'owner') and app.owner == user.owner]
            
        except Exception as e:
            logger.error(f"Error getting user applications: {e}")
            return []

casdoor_client = CasdoorAPIClient()