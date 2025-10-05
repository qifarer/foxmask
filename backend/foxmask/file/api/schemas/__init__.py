# -*- coding: utf-8 -*-
# foxmask/file/api/schemas/__init__.py
from .base import BaseResponse, PaginationParams, ListResponse
from .upload import (
    # 请求 schemas
    InitializeUploadRequest, UploadChunkRequest, CompleteUploadRequest,
    UploadTaskCreateRequest, UploadTaskUpdateRequest, 
    UploadTaskFileCreateRequest, UploadTaskFileUpdateRequest,
    
    # 响应 schemas  
    InitializeUploadResponse, UploadChunkResponse, CompleteUploadResponse,
    GetUploadTaskResponse, ListUploadTasksResponse, ListUploadTaskFilesResponse,
    ResumeUploadResponse, UploadProgressResponse, UploadTaskStatsResponse,
    UploadTaskResponse, UploadTaskListResponse, UploadTaskFileResponse, 
    UploadTaskFileListResponse,
    
    # 查询参数
    UploadTaskQueryParams, UploadTaskFileQueryParams,
    
    # 实体 schemas
    UploadTaskSchema, UploadTaskFileSchema, UploadTaskFileChunkSchema,
    UploadProgressSchema, FileUploadProgressSchema, UploadTaskStatsSchema,
    UploadResumeInfoSchema,
    
    # 枚举
    UploadProcStatusEnum, UploadSourceTypeEnum, UploadStrategyEnum, FileTypeEnum,
    Status, Visibility
)
from .management import (
    FileCreateRequest, FileUpdateRequest, FileResponse, FileListResponse,
    FileQueryParams, FileStatsResponse, FileUploadRequest, FileUploadResponse,
    FileDownloadResponse,
    FileStatus
)

__all__ = [
    # 基础
    "BaseResponse", "PaginationParams", "ListResponse",
    
    # 上传任务 - 请求
    "InitializeUploadRequest", "UploadChunkRequest", "CompleteUploadRequest",
    "UploadTaskCreateRequest", "UploadTaskUpdateRequest",
    "UploadTaskFileCreateRequest", "UploadTaskFileUpdateRequest",
    
    # 上传任务 - 响应
    "InitializeUploadResponse", "UploadChunkResponse", "CompleteUploadResponse",
    "GetUploadTaskResponse", "ListUploadTasksResponse", "ListUploadTaskFilesResponse",
    "ResumeUploadResponse", "UploadProgressResponse", "UploadTaskStatsResponse",
    "UploadTaskResponse", "UploadTaskListResponse", "UploadTaskFileResponse",
    "UploadTaskFileListResponse",
    
    # 上传任务 - 查询
    "UploadTaskQueryParams", "UploadTaskFileQueryParams",
    
    # 上传任务 - 实体
    "UploadTaskSchema", "UploadTaskFileSchema", "UploadTaskFileChunkSchema",
    "UploadProgressSchema", "FileUploadProgressSchema", "UploadTaskStatsSchema",
    "UploadResumeInfoSchema",
    
    # 上传任务 - 枚举
    "UploadProcStatusEnum", "UploadSourceTypeEnum", "UploadStrategyEnum", "FileTypeEnum",
    "Status", "Visibility",
    
    # 文件管理
    "FileCreateRequest", "FileUpdateRequest", "FileResponse", "FileListResponse",
    "FileQueryParams", "FileStatsResponse", "FileUploadRequest", "FileUploadResponse",
    "FileDownloadResponse",
    "FileStatus"
]