from typing import Optional, List, Dict, Any
from .models import APIKey, APIKeyStatus, APIKeyUsage, RateLimitWindow
from foxmask.utils.casdoor_client import casdoor_client
from foxmask.core.config import settings
from foxmask.core.logger import logger
from datetime import datetime, timedelta
from beanie.operators import And

class AuthService:
    async def create_api_key(
        self,
        name: str,
        casdoor_user_id: str,
        permissions: List[str],
        description: Optional[str] = None,
        expires_days: Optional[int] = None,
        allowed_ips: Optional[List[str]] = None,
        allowed_origins: Optional[List[str]] = None,
        rate_limits: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """通过Casdoor创建API Key"""
        # 验证用户是否存在
        user = await casdoor_client.async_sdk.get_user(casdoor_user_id)
        if not user:
            raise ValueError("Casdoor user not found")
        
        # 生成API Key
        raw_key = APIKey.generate_api_key()
        
        # 设置过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        else:
            expires_at = datetime.utcnow() + timedelta(days=settings.API_KEY_DEFAULT_EXPIRE_DAYS)
        
        # 创建API Key记录
        api_key = APIKey(
            name=name,
            description=description,
            casdoor_user_id=casdoor_user_id,
            casdoor_app_id=settings.CASDOOR_APP_NAME,
            key_hash=APIKey.hash_api_key(raw_key),
            key_prefix=raw_key.split('_')[0] + '_',
            permissions=permissions,
            allowed_ips=allowed_ips or [],
            allowed_origins=allowed_origins or [],
            rate_limit_per_minute=rate_limits.get('per_minute', settings.RATE_LIMIT_PER_MINUTE) if rate_limits else casdoor_config.RATE_LIMIT_PER_MINUTE,
            rate_limit_per_hour=rate_limits.get('per_hour', settings.RATE_LIMIT_PER_HOUR) if rate_limits else casdoor_config.RATE_LIMIT_PER_HOUR,
            expires_at=expires_at,
            created_by=casdoor_user_id
        )
        
        await api_key.insert()
        
        return {
            "id": str(api_key.id),
            "name": api_key.name,
            "api_key": raw_key,  # 只在创建时返回一次
            "permissions": api_key.permissions,
            "expires_at": api_key.expires_at,
            "created_at": api_key.created_at
        }

    async def validate_api_key(
        self,
        api_key_str: str,
        required_permission: str,
        client_ip: str,
        origin: Optional[str] = None
    ) -> Optional[APIKey]:
        """验证API Key并检查权限"""
        # 计算哈希值
        key_hash = APIKey.hash_api_key(api_key_str)
        
        # 查找API Key
        api_key = await APIKey.find_one(APIKey.key_hash == key_hash)
        if not api_key:
            return None
        
        # 检查状态
        if not api_key.is_active():
            return None
        
        # 检查IP访问
        if not api_key.can_access_from_ip(client_ip):
            return None
        
        # 检查来源访问
        if origin and not api_key.can_access_from_origin(origin):
            return None
        
        # 检查权限
        if not api_key.has_permission(required_permission):
            return None
        
        # 更新使用统计
        api_key.total_requests += 1
        api_key.last_used = datetime.utcnow()
        api_key.last_ip = client_ip
        await api_key.save()
        
        return api_key

    async def check_rate_limit(
        self,
        api_key_id: str,
        window_type: str = "minute"
    ) -> bool:
        """检查速率限制"""
        now = datetime.utcnow()
        
        if window_type == "minute":
            window_start = now.replace(second=0, microsecond=0)
        elif window_type == "hour":
            window_start = now.replace(minute=0, second=0, microsecond=0)
        else:
            window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查找或创建速率限制窗口
        rate_window = await RateLimitWindow.find_one(
            And(
                RateLimitWindow.api_key_id == api_key_id,
                RateLimitWindow.window_type == window_type,
                RateLimitWindow.window_start == window_start
            )
        )
        
        if not rate_window:
            rate_window = RateLimitWindow(
                api_key_id=api_key_id,
                window_type=window_type,
                window_start=window_start
            )
        
        # 获取API Key的速率限制配置
        api_key = await APIKey.get(api_key_id)
        if not api_key:
            return False
        
        max_requests = getattr(api_key, f"rate_limit_per_{window_type}")
        
        if rate_window.request_count >= max_requests:
            return False
        
        rate_window.request_count += 1
        await rate_window.save()
        
        return True

    async def log_api_usage(
        self,
        api_key_id: str,
        endpoint: str,
        method: str,
        ip_address: str,
        response_status: int,
        processing_time: float,
        user_agent: Optional[str] = None
    ):
        """记录API使用情况"""
        usage_log = APIKeyUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            response_status=response_status,
            processing_time=processing_time
        )
        await usage_log.insert()

    async def revoke_api_key(self, api_key_id: str, revoked_by: str) -> bool:
        """撤销API Key"""
        api_key = await APIKey.get(api_key_id)
        if not api_key:
            return False
        
        api_key.status = APIKeyStatus.REVOKED
        api_key.revoked_at = datetime.utcnow()
        api_key.updated_at = datetime.utcnow()
        await api_key.save()
        
        return True

    async def list_user_api_keys(self, casdoor_user_id: str) -> List[APIKey]:
        """获取用户的所有API Keys"""
        return await APIKey.find(
            APIKey.casdoor_user_id == casdoor_user_id
        ).to_list()

    async def get_api_key_stats(self, api_key_id: str) -> Dict[str, Any]:
        """获取API Key统计信息"""
        # 今日使用量
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_usage = await APIKeyUsage.find(
            And(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= today_start
            )
        ).count()
        
        # 总使用量
        total_usage = await APIKeyUsage.find(
            APIKeyUsage.api_key_id == api_key_id
        ).count()
        
        return {
            "today_usage": today_usage,
            "total_usage": total_usage,
            "last_used": (await APIKey.get(api_key_id)).last_used if await APIKey.get(api_key_id) else None
        }

auth_service = AuthService()