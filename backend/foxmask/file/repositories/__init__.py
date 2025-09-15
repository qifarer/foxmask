# foxmask/file/repositories/__init__.py

from .file import file_repository
from .minio import minio_repository

__all__ = ['file_repository', 'minio_repository']