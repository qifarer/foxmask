from fastapi import Request
from typing import Dict

async def get_i18n_messages(request: Request) -> Dict[str, str]:
    """获取国际化消息"""
    # 这里可以集成真正的 i18n 库
    return {
        "upload.fileOnlySupportInServerMode": "File type {ext} is only supported in server mode with {cloud}",
        "error": "Error"
    }