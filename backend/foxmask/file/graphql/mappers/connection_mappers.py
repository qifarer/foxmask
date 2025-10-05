# mappers/connection_mappers.py
from typing import List, Optional
from .base import BaseMapper
from .upload_mappers import UploadTaskMapper, UploadTaskFileMapper, UploadTaskFileChunkMapper
from foxmask.file.dtos.upload import *
from foxmask.file.graphql.schemas.upload import *
from foxmask.core.schema import *

class UploadTaskConnectionMapper(BaseMapper):
    """上传任务连接类型映射器"""
    
    @staticmethod
    def create_connection(
        task_dtos: List[UploadTaskDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> List[UploadTask]:
        """从 DTO 列表创建 GraphQL 类型列表"""
        # 直接返回映射后的列表，因为我们不再使用 Relay Connection
        return [
            UploadTaskMapper.dto_to_schema(task_dto)
            for task_dto in task_dtos
        ]
    
    @staticmethod
    def create_paginated_response(
        task_dtos: List[UploadTaskDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> ListUploadTasksResponse:
        """创建分页响应"""
        data = [
            UploadTaskMapper.dto_to_schema(task_dto)
            for task_dto in task_dtos
        ]
        
        has_next_page = (skip + limit) < total_count
        has_previous_page = skip > 0
        
        # 创建分页信息
        pagination_info = PageInfo(
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            total_count=total_count,
            current_page=(skip // limit) + 1 if limit > 0 else 1,
            total_pages=(total_count + limit - 1) // limit if limit > 0 else 1
        )
        
        return ListUploadTasksResponse(
            success=True,
            data=data,
            pagination=pagination_info
        )


class UploadTaskFileConnectionMapper(BaseMapper):
    """上传任务文件连接类型映射器"""
    
    @staticmethod
    def create_connection(
        file_dtos: List[UploadTaskFileDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> List[UploadTaskFile]:
        """从文件 DTO 列表创建 GraphQL 类型列表"""
        return [
            UploadTaskFileMapper.dto_to_schema(file_dto)
            for file_dto in file_dtos
        ]
    
    @staticmethod
    def create_paginated_response(
        file_dtos: List[UploadTaskFileDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> ListUploadTaskFilesResponse:
        """创建分页响应"""
        data = [
            UploadTaskFileMapper.dto_to_schema(file_dto)
            for file_dto in file_dtos
        ]
        
        has_next_page = (skip + limit) < total_count
        has_previous_page = skip > 0
        
        pagination_info = PageInfo(
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            total_count=total_count,
            current_page=(skip // limit) + 1 if limit > 0 else 1,
            total_pages=(total_count + limit - 1) // limit if limit > 0 else 1
        )
        
        return ListUploadTaskFilesResponse(
            success=True,
            data=data,
            pagination=pagination_info
        )


class UploadTaskFileChunkConnectionMapper(BaseMapper):
    """上传任务文件分块连接类型映射器"""
    
    @staticmethod
    def create_connection(
        chunk_dtos: List[UploadTaskFileChunkDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> List[UploadTaskFileChunk]:
        """从分块 DTO 列表创建 GraphQL 类型列表"""
        return [
            UploadTaskFileChunkMapper.dto_to_schema(chunk_dto)
            for chunk_dto in chunk_dtos
        ]
    
    @staticmethod
    def create_paginated_response(
        chunk_dtos: List[UploadTaskFileChunkDTO],
        total_count: int,
        skip: int,
        limit: int
    ) -> ListUploadTaskFileChunksResponse:
        """创建分页响应"""
        data = [
            UploadTaskFileChunkMapper.dto_to_schema(chunk_dto)
            for chunk_dto in chunk_dtos
        ]
        
        has_next_page = (skip + limit) < total_count
        has_previous_page = skip > 0
        
        pagination_info = PageInfo(
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            total_count=total_count,
            current_page=(skip // limit) + 1 if limit > 0 else 1,
            total_pages=(total_count + limit - 1) // limit if limit > 0 else 1
        )
        
        return ListUploadTaskFileChunksResponse(
            success=True,
            data=data,
            pagination=pagination_info
        )


class PaginationHelper:
    """分页辅助类"""
    
    @staticmethod
    def create_page_info(
        total_count: int,
        skip: int,
        limit: int
    ) -> PageInfo:
        """创建分页信息"""
        if limit <= 0:
            return PageInfo(
                has_next_page=False,
                has_previous_page=False,
                total_count=total_count,
                current_page=1,
                total_pages=1
            )
        
        current_page = (skip // limit) + 1
        total_pages = (total_count + limit - 1) // limit
        has_next_page = (skip + limit) < total_count
        has_previous_page = skip > 0
        
        return PageInfo(
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
            total_count=total_count,
            current_page=current_page,
            total_pages=total_pages
        )
    
    @staticmethod
    def calculate_pagination_params(
        page: int,
        page_size: int
    ) -> tuple[int, int]:
        """计算分页参数"""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100
            
        skip = (page - 1) * page_size
        return skip, page_size