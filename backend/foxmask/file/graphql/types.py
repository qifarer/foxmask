# foxmask/file/graphql/types.py
import strawberry
from typing import Optional, Dict, Any
from strawberry.scalars import JSON

@strawberry.type
class Error:
    """错误类型"""
    message: str
    code: str
    details: Optional[JSON] = None

@strawberry.type
class SuccessResponse:
    """成功响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[Error] = None

@strawberry.type
class FileType:
    """文件类型（共享）"""
    id: strawberry.ID
    filename: str
    file_size: int
    content_type: str
    file_type: "FileTypeEnum"
    status: "FileStatusEnum"
    upload_progress: float
    uploaded_by: str
    tenant_id: str
    created_at: str
    updated_at: str

# 错误处理函数
def handle_error(message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict] = None) -> Error:
    """创建标准错误响应"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error {code}: {message}. Details: {details}")
    return Error(message=message, code=code, details=details)