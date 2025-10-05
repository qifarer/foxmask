# -*- coding: utf-8 -*-
# foxmask/file/service/__init__.py
"""
文件管理模块 Service 包
"""

from .management import FileService, FileLogService
from .upload import UploadService


class ServiceManager:
    """Service管理器"""
    
    def __init__(self):
        self._file_service = None
        self._file_log_service = None
        self._upload_task_service = None
    
    @property
    def file_service(self) -> FileService:
        """获取文件服务"""
        if self._file_service is None:
            self._file_service = FileService()
        return self._file_service
    
    @property
    def file_log_service(self) -> FileLogService:
        """获取文件日志服务"""
        if self._file_log_service is None:
            self._file_log_service = FileLogService()
        return self._file_log_service
    
    @property
    def upload_task_service(self) -> UploadService:
        """获取上传任务服务"""
        if self._upload_task_service is None:
            self._upload_task_service = UploadService()
        return self._upload_task_service


# 全局Service管理器实例
_file_service_manager: ServiceManager = None

def get_service_manager() -> ServiceManager:
    """获取Service管理器实例"""
    global _file_service_manager
    if _file_service_manager is None:
        _file_service_manager = ServiceManager()
    return _file_service_manager


# 导出所有Service类和管理器
__all__ = [
    "ServiceManager",
    "FileService", 
    "FileLogService",
    "UploadTaskService",
    "get_service_manager"
]