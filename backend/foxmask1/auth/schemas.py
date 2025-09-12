# foxmask/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any, ClassVar
from datetime import datetime
from pydantic.json_schema import SkipJsonSchema

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")
    avatar: Optional[str] = Field(None, description="头像URL")

class UserCreate(UserBase):
    """创建用户时的Schema"""
    password: Optional[str] = Field(None, description="密码")

class UserUpdate(BaseModel):
    """更新用户时的Schema"""
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    avatar: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    """完整的用户模型（包含Casdoor特定字段）"""
    id: str = Field(..., description="用户ID")
    is_active: bool = Field(True, description="是否激活")
    is_verified: bool = Field(False, description="是否已验证邮箱")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # Casdoor 特定字段
    casdoor_user_id: Optional[str] = Field(None, description="Casdoor用户ID")
    casdoor_org: Optional[str] = Field(None, description="Casdoor组织名称")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    
    # 权限相关字段
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    
    # 用户属性（扩展字段）
    properties: Dict[str, Any] = Field(default_factory=dict, description="用户属性")
    
    # Pydantic V2 配置
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "user-123456",
                "username": "john_doe",
                "email": "john@example.com",
                "display_name": "John Doe",
                "avatar": "https://example.com/avatar.jpg",
                "is_active": True,
                "is_verified": True,
                "roles": ["user", "editor"],
                "permissions": ["read", "write"],
                "casdoor_user_id": "casdoor_user_789",
                "casdoor_org": "foxmask",
                "tenant_id": "tenant-001"
            }
        }
    )

class UserInDB(User):
    """数据库中的用户模型（包含敏感信息）"""
    hashed_password: Optional[str] = Field(None, description="哈希后的密码")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    login_count: int = Field(0, description="登录次数")

class UserPublic(UserBase):
    """公开的用户信息（不包含敏感字段）"""
    id: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime]
    roles: List[str]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "user-123456",
                "username": "john_doe",
                "email": "john@example.com",
                "display_name": "John Doe",
                "avatar": "https://example.com/avatar.jpg",
                "is_active": True,
                "is_verified": True,
                "roles": ["user", "editor"]
            }
        }
    )

class Token(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: Optional[int] = Field(3600, description="过期时间（秒）")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "refresh_token_123456"
            }
        }
    )

class TokenData(BaseModel):
    """Token中包含的数据"""
    sub: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    roles: List[str] = Field(default_factory=list, description="角色")
    exp: Optional[int] = Field(None, description="过期时间戳")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sub": "user-123456",
                "username": "john_doe",
                "email": "john@example.com",
                "roles": ["user", "editor"],
                "exp": 1672531200
            }
        }
    )

class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "password123",
                "remember_me": True
            }
        }
    )

class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    display_name: Optional[str] = Field(None, description="显示名称")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "password123",
                "display_name": "John Doe"
            }
        }
    )

class AuthResponse(BaseModel):
    """认证响应模型"""
    user: UserPublic
    token: Token
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "user-123456",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "display_name": "John Doe",
                    "avatar": "https://example.com/avatar.jpg",
                    "is_active": True,
                    "is_verified": True,
                    "roles": ["user", "editor"]
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "refresh_token": "refresh_token_123456"
                }
            }
        }
    )

class Permission(BaseModel):
    """权限模型"""
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "files:delete",
                "description": "删除文件的权限"
            }
        }
    )

class Role(BaseModel):
    """角色模型"""
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    permissions: List[Permission] = Field(default_factory=list, description="权限列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "admin",
                "description": "系统管理员",
                "permissions": [
                    {"name": "users:manage", "description": "管理用户"},
                    {"name": "files:delete", "description": "删除文件"}
                ]
            }
        }
    )

# 响应模型
class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息内容")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "操作成功"
            }
        }
    )

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "认证失败",
                "details": {"reason": "无效的token"}
            }
        }
    )

# 新增：Casdoor 特定的响应模型
class CasdoorUserInfo(BaseModel):
    """Casdoor 用户信息响应"""
    sub: str = Field(..., description="用户标识")
    name: Optional[str] = Field(None, description="姓名")
    preferred_username: str = Field(..., description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    email_verified: bool = Field(False, description="邮箱是否验证")
    picture: Optional[str] = Field(None, description="头像")
    updated_at: Optional[int] = Field(None, description="更新时间戳")
    
    # Casdoor 特定字段
    id: Optional[str] = Field(None, description="Casdoor用户ID")
    owner: Optional[str] = Field(None, description="所属组织")
    type: Optional[str] = Field(None, description="用户类型")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="权限列表")

class OIDCConfig(BaseModel):
    """OIDC 配置信息"""
    issuer: str = Field(..., description="发行者")
    authorization_endpoint: str = Field(..., description="授权端点")
    token_endpoint: str = Field(..., description="令牌端点")
    userinfo_endpoint: str = Field(..., description="用户信息端点")
    jwks_uri: str = Field(..., description="JWKS URI")
    scopes_supported: List[str] = Field(default_factory=list, description="支持的scope")
    response_types_supported: List[str] = Field(default_factory=list, description="支持的响应类型")

# 新增：分页响应模型
class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "size": 10,
                "has_next": False,
                "has_prev": False
            }
        }
    )

# 新增：用户列表响应
class UserListResponse(PaginatedResponse):
    """用户列表响应"""
    items: List[UserPublic] = Field(..., description="用户列表")