from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from foxmask.core.config import get_settings

settings = get_settings()

class FileSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 检查 content-length 头
        content_length = request.headers.get('content-length')
        if content_length:
            file_size = int(content_length)
            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"
                )
        
        response = await call_next(request)
        return response