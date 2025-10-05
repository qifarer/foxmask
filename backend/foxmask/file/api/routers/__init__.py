# -*- coding: utf-8 -*-
# foxmask/file/api/__init__.py
"""
文件管理模块 REST API 包
"""

# from .management import router as file_router
from .upload import router as upload_router

# 导出所有路由
__all__ = ["file_router", "upload_router"]