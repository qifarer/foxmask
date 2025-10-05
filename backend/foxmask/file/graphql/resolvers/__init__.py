# -*- coding: utf-8 -*-
# foxmask/file/graphql/resolvers/__init__.py
"""
文件管理模块 GraphQL Resolvers 包
"""

from .management import FileQuery, FileMutation, FileUploadMutation
from .upload import UploadQuery, UploadMutation

__all__ = [
    "FileQuery",
    "FileMutation",
    "FileUploadMutation",
    "UploadQuery",
    "UploadMutation",
]
