# -*- coding: utf-8 -*-
# foxmask/file/dto/__init__.py
"""
文件管理模块 DTO 包
"""

from .upload import *

from .management import (
    FileCreateDTO,
    FileUpdateDTO,
    FileResponseDTO,
    FileQueryDTO,
    FileListDTO,
    FileLogCreateDTO,
    FileLogResponseDTO,
    FileLogQueryDTO,
    FileLogListDTO,
    FileStatsDTO,
    FileOperationStatsDTO,
)

# 上传模块DTO导出
__all_upload__ = [
    UploadTaskFileChunkDTO,
    UploadTaskFileDTO,
    UploadTaskDTO,
    InitializeUploadInputDTO,
    InitializeUploadFileInputDTO,
    UploadChunkInputDTO,
    CompleteUploadInputDTO,
    UploadTaskQueryDTO
]

# 文件管理模块DTO导出
__all_management__ = [
    FileCreateDTO,
    FileUpdateDTO,
    FileResponseDTO,
    FileQueryDTO,
    FileListDTO,
    FileLogCreateDTO,
    FileLogResponseDTO,
    FileLogQueryDTO,
    FileLogListDTO,
    FileStatsDTO,
    FileOperationStatsDTO,
]

# 合并所有导出
__all__ = __all_upload__ + __all_management__