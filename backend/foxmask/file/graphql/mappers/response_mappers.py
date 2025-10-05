# mappers/response_mappers.py
from typing import List, Optional
from .base import BaseMapper
from .upload_mappers import UploadTaskMapper, UploadTaskFileMapper, UploadTaskFileChunkMapper
from .connection_mappers import UploadTaskConnectionMapper, UploadTaskFileConnectionMapper, UploadTaskFileChunkConnectionMapper
from foxmask.file.dtos.upload import *
from foxmask.file.graphql.schemas.upload import *

class UploadResponseMapper(BaseMapper):
    """上传响应映射器"""
    
    @staticmethod
    def to_initialize_response(task_dto: UploadTaskDTO) -> InitializeUploadResponse:
        """转换为初始化上传响应"""
        return InitializeUploadResponse(
            success=True,
            message="Upload task initialized successfully",
            data=UploadTaskMapper.dto_to_schema(task_dto)
        )
    
    @staticmethod
    def to_upload_chunk_response(
        chunk_dto: UploadTaskFileChunkDTO,
        next_chunk: Optional[int] = None,
        progress: Optional[float] = None,
        is_completed: Optional[bool] = None
    ) -> UploadChunkResponse:
        """转换为上传分块响应"""
        return UploadChunkResponse(
            success=True,
            message="Chunk uploaded successfully",
            data=UploadTaskFileChunkMapper.dto_to_schema(chunk_dto),
            next_chunk=next_chunk,
            progress=progress,
            is_completed=is_completed
        )
    
    @staticmethod
    def to_complete_upload_response(task_dto: UploadTaskDTO) -> CompleteUploadResponse:
        """转换为完成上传响应"""
        return CompleteUploadResponse(
            success=True,
            message="Upload completed successfully",
            data=UploadTaskMapper.dto_to_schema(task_dto)
        )
    
    @staticmethod
    def to_get_upload_task_response(task_dto: UploadTaskDTO) -> GetUploadTaskResponse:
        """转换为获取上传任务响应"""
        return GetUploadTaskResponse(
            success=True,
            message="Upload task retrieved successfully",
            data=UploadTaskMapper.dto_to_schema(task_dto)
        )
    
    @staticmethod
    def to_list_upload_tasks_response(
        task_dtos: List[UploadTaskDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> ListUploadTasksResponse:
        """转换为上传任务列表响应"""
        connection = UploadTaskConnectionMapper.create_connection(
            task_dtos=task_dtos,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
        return ListUploadTasksResponse(
            success=True,
            message="Upload tasks retrieved successfully",
            data=connection
        )
    
    @staticmethod
    def to_list_upload_task_files_response(
        file_dtos: List[UploadTaskFileDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> ListUploadTaskFilesResponse:
        """转换为上传任务文件列表响应"""
        connection = UploadTaskFileConnectionMapper.create_connection(
            file_dtos=file_dtos,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
        return ListUploadTaskFilesResponse(
            success=True,
            message="Upload task files retrieved successfully",
            data=connection
        )
    
    @staticmethod
    def to_resume_upload_response(
        task_dto: UploadTaskDTO,
        resumed_files: Optional[List[str]] = None,
        total_files_to_resume: int = 0
    ) -> ResumeUploadResponse:
        """转换为恢复上传响应"""
        return ResumeUploadResponse(
            success=True,
            message="Upload resumed successfully",
            data=UploadTaskMapper.dto_to_schema(task_dto),
            resumed_files=resumed_files or [],
            total_files_to_resume=total_files_to_resume
        )