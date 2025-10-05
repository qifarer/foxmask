# -*- coding: utf-8 -*-
# foxmask/file/repository/__init__.py
"""
文件管理模块 Repository 包 - 直接数据操作版本
"""

from .management import FileRepository, FileLogRepository
from .upload import UploadTaskRepository,UploadTaskFileChunkRepository,UploadTaskFileRepository
from .minio import MinIORepository

class RepositoryManager:
    """Repository管理器"""
    
    def __init__(self):
        self._file_repo = None
        self._file_log_repo = None
        self._upload_task_repo = None
        self._upload_task_file_repo = None
        self._upload_task_file_chunk_repo = None
        self._minio_repo = None
    
    @property
    def minio_repository(self) -> MinIORepository:
        """获取文件Repository"""
        if self._minio_repo is None:
            self._minio_repo = MinIORepository()
        return self._minio_repo
    
    @property
    def file_repository(self) -> FileRepository:
        """获取文件Repository"""
        if self._file_repo is None:
            self._file_repo = FileRepository()
        return self._file_repo
    
    @property
    def file_log_repository(self) -> FileLogRepository:
        """获取文件日志Repository"""
        if self._file_log_repo is None:
            self._file_log_repo = FileLogRepository()
        return self._file_log_repo
    
    @property
    def upload_task_repository(self) -> UploadTaskRepository:
        """获取上传任务Repository"""
        if self._upload_task_repo is None:
            self._upload_task_repo = UploadTaskRepository()
        return self._upload_task_repo

    @property
    def upload_task_file_repository(self) -> UploadTaskFileRepository:
        """获取上传任务Repository"""
        if self._upload_task_file_repo is None:
            self._upload_task_file_repo = UploadTaskFileRepository()
        return self._upload_task_file_repo
     
    @property
    def upload_task_file_chunk_repository(self) -> UploadTaskFileChunkRepository:
        """获取上传任务Repository"""
        if self._upload_task_file_chunk_repo is None:
            self._upload_task_file_chunk_repo = UploadTaskFileChunkRepository()
        return self._upload_task_file_chunk_repo
   
# 全局Repository管理器实例
_file_repository_manager: RepositoryManager = None

def get_repository_manager() -> RepositoryManager:
    """获取Repository管理器实例"""
    global _file_repository_manager
    if _file_repository_manager is None:
        _file_repository_manager = RepositoryManager()
    return _file_repository_manager


# 导出所有Repository类和管理器
__all__ = [
    "get_repository_manager"
]