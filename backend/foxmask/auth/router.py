from fastapi import APIRouter, Depends, HTTPException, status, Request
from .services import auth_service
from .models import APIKeyStatus
from foxmask.shared.dependencies import require_admin, get_api_context
from typing import List, Optional
from foxmask.core.logger import logger

router = APIRouter(tags=["api-keys"])

@router.post("/api-keys", response_model=dict)
async def create_api_key(
    request: Request,
    name: str,
    permissions: List[str],
    description: Optional[str] = None,
    expires_days: Optional[int] = None,
    allowed_ips: Optional[List[str]] = None,
    allowed_origins: Optional[List[str]] = None,
    rate_limits: Optional[dict] = None,
    context: dict = Depends(require_admin)
):
    """创建新的API Key（需要admin权限）"""
    try:
        result = await auth_service.create_api_key(
            name=name,
            casdoor_user_id=context["user_id"],
            permissions=permissions,
            description=description,
            expires_days=expires_days,
            allowed_ips=allowed_ips,
            allowed_origins=allowed_origins,
            rate_limits=rate_limits
        )
        
        return {
            "success": True,
            "data": result,
            "message": "API Key created successfully. Save the key now as it won't be shown again!"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/api-keys", response_model=dict)
async def list_api_keys(context: dict = Depends(require_admin)):
    """获取当前用户的所有API Keys"""
    try:
        api_keys = await auth_service.list_user_api_keys(context["user_id"])
        
        return {
            "success": True,
            "data": [
                {
                    "id": str(key.id),
                    "name": key.name,
                    "status": key.status,
                    "permissions": key.permissions,
                    "created_at": key.created_at,
                    "expires_at": key.expires_at,
                    "last_used": key.last_used,
                    "total_requests": key.total_requests
                }
                for key in api_keys
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/api-keys/{api_key_id}/stats", response_model=dict)
async def get_api_key_stats(
    api_key_id: str,
    context: dict = Depends(require_admin)
):
    """获取API Key统计信息"""
    try:
        # 验证API Key属于当前用户
        api_keys = await auth_service.list_user_api_keys(context["user_id"])
        if not any(str(key.id) == api_key_id for key in api_keys):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        
        stats = await auth_service.get_api_key_stats(api_key_id)
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API key stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.delete("/api-keys/{api_key_id}", response_model=dict)
async def revoke_api_key(
    api_key_id: str,
    context: dict = Depends(require_admin)
):
    """撤销API Key"""
    try:
        # 验证API Key属于当前用户
        api_keys = await auth_service.list_user_api_keys(context["user_id"])
        if not any(str(key.id) == api_key_id for key in api_keys):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")
        
        success = await auth_service.revoke_api_key(api_key_id, context["user_id"])
        
        if success:
            return {"success": True, "message": "API Key revoked successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke API Key")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/verify", response_model=dict)
async def verify_api_key(context: dict = Depends(get_api_context)):
    """验证API Key有效性"""
    return {
        "success": True,
        "data": {
            "api_key_id": context["api_key_id"],
            "user_id": context["user_id"],
            "permissions": context["permissions"],
            "valid": True
        }
    }