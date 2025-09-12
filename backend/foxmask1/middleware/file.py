# foxmask/middleware/file.py
import re
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from foxmask.core.config import get_settings

settings = get_settings()

class FileSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):  # 默认10MB
        super().__init__(app)
        self.max_file_size = settings.MAX_FILE_SIZE
    
    async def dispatch(self, request: Request, call_next):
        # 检查内容类型是否为文件上传
        content_type = request.headers.get("content-type", "")
        
        # 判断是否是文件上传请求
        is_file_upload = (
            request.method == "POST" and 
            (
                content_type.startswith("multipart/form-data") or
                content_type.startswith("application/octet-stream") or
                re.search(r"file|upload", request.url.path, re.IGNORECASE)
            )
        )
        
        if is_file_upload:
            # 获取内容长度
            content_length = request.headers.get("content-length")
            
            if content_length:
                file_size = int(content_length)
                
                # 检查文件大小
                if file_size > self.max_file_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size is {self.max_file_size} bytes"
                    )
            
            # 对于分块上传，需要流式处理
            elif content_type.startswith("multipart/form-data"):
                # 对于multipart请求，我们无法预先知道大小，需要在处理过程中检查
                # 这里我们只是记录警告，实际大小检查应该在路由处理中进行
                pass
        
        # 继续处理请求
        response = await call_next(request)
        return response    