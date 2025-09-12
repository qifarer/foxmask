from beanie import Document, Indexed
from pydantic import Field, ConfigDict
from typing import Optional, List, Dict, ClassVar
from datetime import datetime, timedelta
from enum import Enum
import secrets
import hashlib

class APIKeyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"

class APIKey(Document):
    # Casdoor 关联信息
    casdoor_user_id: Indexed(str)  # Casdoor 用户ID
    casdoor_app_id: str  # Casdoor 应用ID
    
    # API Key 信息
    name: str
    description: Optional[str] = None
    key_hash: Indexed(str, unique=True)  # 哈希后的API Key
    key_prefix: str = Field(default="fox_")
    
    # 权限控制
    permissions: List[str] = Field(default_factory=list)
    allowed_ips: List[str] = Field(default_factory=list)
    allowed_origins: List[str] = Field(default_factory=list)
    
    # 限制配置
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_per_hour: int = Field(default=5000)
    max_requests_per_day: Optional[int] = None
    
    # 状态管理
    status: APIKeyStatus = Field(default=APIKeyStatus.ACTIVE)
    total_requests: int = Field(default=0)
    last_used: Optional[datetime] = None
    last_ip: Optional[str] = None
    
    # 有效期
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    
    # 元数据
    created_by: str  # 创建者用户ID
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # 使用新的 ConfigDict 方式
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "casdoor_user_id": "user_123",
                "casdoor_app_id": "app_456",
                "name": "My API Key",
                "description": "For testing purposes",
                "key_hash": "sha256_hash_here",
                "key_prefix": "fox_",
                "permissions": ["read", "write"],
                "allowed_ips": ["192.168.1.1"],
                "allowed_origins": ["https://example.com"],
                "rate_limit_per_minute": 100,
                "rate_limit_per_hour": 5000,
                "max_requests_per_day": 10000,
                "status": "active",
                "total_requests": 0,
                "created_by": "user_123"
            }
        }
    )

    class Settings:
        name = "casdoor_api_keys"
        indexes = [
            "casdoor_user_id",
            "key_hash", 
            "status",
            "expires_at",
            "created_at"
        ]

    @staticmethod
    def generate_api_key(prefix: str = "fox_", length: int = 32) -> str:
        """生成新的API Key"""
        random_part = secrets.token_urlsafe(length)
        return f"{prefix}{random_part}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """对API Key进行安全哈希"""
        salt = "casdoor_api_key_salt"
        return hashlib.sha256(f"{salt}{api_key}".encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> bool:
        """验证API Key"""
        return self.key_hash == self.hash_api_key(api_key)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    def is_active(self) -> bool:
        """检查是否活跃"""
        return self.status == APIKeyStatus.ACTIVE and not self.is_expired()

    def has_permission(self, permission: str) -> bool:
        """检查是否有特定权限"""
        return permission in self.permissions or "admin" in self.permissions

    def can_access_from_ip(self, ip: str) -> bool:
        """检查IP是否在白名单中"""
        if not self.allowed_ips:
            return True
        return ip in self.allowed_ips

    def can_access_from_origin(self, origin: str) -> bool:
        """检查来源是否在白名单中"""
        if not self.allowed_origins:
            return True
        return origin in self.allowed_origins

class APIKeyUsage(Document):
    """API Key 使用记录"""
    api_key_id: Indexed(str)
    endpoint: str
    method: str
    ip_address: str
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_status: int
    processing_time: float  # 处理时间（秒）
    
    # 使用新的 ConfigDict 方式
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": "key_123",
                "endpoint": "/api/v1/files",
                "method": "GET",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "response_status": 200,
                "processing_time": 0.15
            }
        }
    )

    class Settings:
        name = "api_key_usage_logs"
        indexes = [
            "api_key_id",
            "timestamp",
            "endpoint",
            "ip_address"
        ]

class RateLimitWindow(Document):
    """速率限制窗口"""
    api_key_id: Indexed(str)
    window_type: str  # minute, hour, day
    window_start: datetime
    request_count: int = Field(default=0)
    
    # 使用新的 ConfigDict 方式
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key_id": "key_123",
                "window_type": "minute",
                "window_start": "2024-01-01T00:00:00",
                "request_count": 45
            }
        }
    )

    class Settings:
        name = "rate_limit_windows"
        indexes = [
            "api_key_id",
            "window_type", 
            "window_start"
        ]