import strawberry
from strawberry.types import Info
from typing import Optional, List

from foxmask.file.graphql.schemas.enums import *
from foxmask.file.graphql.schemas.upload import *
from foxmask.core.schema import *
from foxmask.file.dtos.upload import *

from foxmask.file.services import get_service_manager
from foxmask.core.logger import logger

# 使用统一的映射器
from foxmask.file.graphql.mappers.upload import UploadMapper


# GraphQL Resolver
@strawberry.type
class UploadMutation:
    def __init__(self):
        self.service = get_service_manager().upload_task_service
    
    @strawberry.mutation
    async def initialize_upload(
        self, 
        info: Info,
        input: InitializeUploadInput
    ) -> InitializeUploadResponse:
        """初始化上传任务"""
        try:
            print('======initialize_upload===000000===')
            print(str(input))
            user_id = info.context.get("user_id", "SYSTEM")
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 使用统一的映射器转换输入
            input_dto = UploadMapper.initialize_upload_input_to_dto(
                input, 
                tenant_id=tenant_id, 
                created_by=user_id
            )
            print('======initialize_upload===111111===')
            # 调用服务层
            response_dto = await self.service.initialize_upload(input_dto)
            print('======initialize_upload===222222===')
            # 使用统一的映射器转换响应
            return UploadMapper.initialize_upload_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"Initialize upload failed: {e}")
            return InitializeUploadResponse(
                success=False,
                errors=[Error(message=f"初始化上传任务失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )
    
        
    @strawberry.mutation
    async def upload_chunk(
        self,
        info: Info,
        input: UploadChunkInput
    ) -> UploadChunkResponse:
        """上传文件块"""
        try:
            logger.info(f"GraphQL upload_chunk called, chunk_data type: {type(input.chunk_data)}")
            
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 使用统一的映射器转换输入
            input_dto = UploadMapper.upload_chunk_input_to_dto(input, tenant_id)
            
            # 调用服务层
            response_dto = await self.service.upload_chunk(input_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.upload_chunk_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"Upload chunk failed: {e}")
            return UploadChunkResponse(
                success=False,
                errors=[Error(message=f"上传文件块失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )
    
    @strawberry.mutation
    async def complete_upload(
        self,
        info: Info,
        input: CompleteUploadInput
    ) -> CompleteUploadResponse:
        """完成文件上传"""
        try:
            # 使用统一的映射器转换输入
            input_dto = UploadMapper.complete_upload_input_to_dto(input)
            
            # 调用服务层
            response_dto = await self.service.complete_upload(input_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.complete_upload_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"Complete upload failed: {e}")
            return CompleteUploadResponse(
                success=False,
                errors=[Error(message=f"完成上传失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )
    
    @strawberry.mutation
    async def resume_upload(
        self,
        info: Info,
        input: ResumeUploadInput
    ) -> ResumeUploadResponse:
        """断点续传"""
        try:
            user_id = info.context.get("user_id", "SYSTEM")
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 使用统一的映射器转换输入
            input_dto = UploadMapper.resume_upload_input_to_dto(
                input, 
                tenant_id=tenant_id, 
                created_by=user_id
            )
            
            # 调用服务层
            response_dto = await self.service.resume_upload(input_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.resume_upload_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")
            return ResumeUploadResponse(
                success=False,
                errors=[Error(message=f"恢复上传失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )


@strawberry.type
class UploadQuery:
    def __init__(self):
        self.service = get_service_manager().upload_task_service
    
    @strawberry.field
    async def get_upload_task(
        self,
        info: Info,
        task_id: str
    ) -> GetUploadTaskResponse:
        """获取上传任务详情"""
        try:
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 调用服务层
            response_dto = await self.service.get_upload_task(task_id, tenant_id)
            
            # 使用统一的映射器转换响应
            return UploadMapper.get_upload_task_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"Get upload task failed: {e}")
            return GetUploadTaskResponse(
                success=False,
                errors=[Error(message=f"获取上传任务失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )
    
    @strawberry.field
    async def list_upload_tasks(
        self,
        info: Info,
        query: Optional[UploadTaskQueryInput] = None,
        pagination: Optional[PaginationInput] = None  # 使用 GraphQL 输入类型
    ) -> ListUploadTasksResponse:
        """分页查询上传任务"""
        try:
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 构建查询DTO
            if query:
                query_dto = UploadMapper.upload_task_query_input_to_dto(query, tenant_id)
            else:
                query_dto = UploadTaskQueryDTO(tenant_id=tenant_id)
            
            # 将 GraphQL 分页输入转换为 DTO 分页参数
            pagination_dto = None
            if pagination:
                pagination_dto = PaginationParams(
                    page=pagination.page,
                    page_size=pagination.page_size,
                    sort_by=pagination.sort_by,
                    sort_order=pagination.sort_order
                )
            else:
                pagination_dto = PaginationParams(
                    page=1,
                    page_size=20,
                    sort_by="created_at",
                    sort_order="desc"
                )
            
            # 调用服务层
            response_dto = await self.service.list_upload_tasks(query_dto, pagination_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.list_upload_tasks_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"List upload tasks failed: {e}")
            return ListUploadTasksResponse(
                success=False,
                errors=[Error(message=f"查询上传任务列表失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None,
                pagination=None
            )
    
    @strawberry.field
    async def list_upload_task_files(
        self,
        info: Info,
        query: UploadTaskFileQueryInput,
        pagination: Optional[PaginationInput] = None  # 使用 GraphQL 输入类型
    ) -> ListUploadTaskFilesResponse:
        """查询任务文件列表"""
        try:
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 构建查询DTO
            query_dto = UploadMapper.upload_task_file_query_input_to_dto(query, tenant_id)
            
            # 将 GraphQL 分页输入转换为 DTO 分页参数
            pagination_dto = None
            if pagination:
                pagination_dto = PaginationParams(
                    page=pagination.page,
                    page_size=pagination.page_size,
                    sort_by=pagination.sort_by,
                    sort_order=pagination.sort_order
                )
            else:
                pagination_dto = PaginationParams(
                    page=1,
                    page_size=50,
                    sort_by="created_at",
                    sort_order="asc"
                )
            
            # 调用服务层
            response_dto = await self.service.list_upload_task_files(query_dto, pagination_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.list_upload_task_files_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"List upload task files failed: {e}")
            return ListUploadTaskFilesResponse(
                success=False,
                errors=[Error(message=f"查询上传任务文件列表失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None,
                pagination=None
            )
    
    @strawberry.field
    async def list_upload_task_file_chunks(
        self,
        info: Info,
        query: UploadTaskFileChunkQueryInput,
        pagination: Optional[PaginationInput] = None  # 使用 GraphQL 输入类型
    ) -> ListUploadTaskFileChunksResponse:
        """查询文件分块列表"""
        try:
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 构建查询DTO
            query_dto = UploadMapper.upload_task_file_chunk_query_input_to_dto(query, tenant_id)
            
            # 将 GraphQL 分页输入转换为 DTO 分页参数
            pagination_dto = None
            if pagination:
                pagination_dto = PaginationParams(
                    page=pagination.page,
                    page_size=pagination.page_size,
                    sort_by=pagination.sort_by,
                    sort_order=pagination.sort_order
                )
            else:
                pagination_dto = PaginationParams(
                    page=1,
                    page_size=100,
                    sort_by="chunk_number",
                    sort_order="asc"
                )
            
            # 调用服务层
            response_dto = await self.service.list_upload_task_file_chunks(query_dto, pagination_dto)
            
            # 使用统一的映射器转换响应
            return UploadMapper.list_upload_task_file_chunks_response_dto_to_schema(response_dto)
            
        except Exception as e:
            logger.error(f"List upload task file chunks failed: {e}")
            return ListUploadTaskFileChunksResponse(
                success=False,
                errors=[Error(message=f"查询文件分块列表失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None,
                pagination=None
            )
    
    @strawberry.field
    async def get_upload_progress(
        self,
        info: Info,
        task_id: str,
        include_file_details: bool = False
    ) -> UploadProgressResponse:
        """获取上传进度"""
        try:
            tenant_id = info.context.get("tenant_id", "foxmask")
            
            # 调用服务层获取进度
            progress_dto = await self.service.get_upload_progress(task_id, tenant_id, include_file_details)
            
            if not progress_dto:
                return UploadProgressResponse(
                    success=False,
                    errors=[Error(message="进度信息不存在", code="PROGRESS_NOT_FOUND")],
                    data=None
                )
            
            # 构建成功响应
            base_response = BaseResponseDTO(success=True, errors=None)
            
            # 使用统一的映射器转换响应
            return UploadMapper.upload_progress_response_dto_to_schema(base_response, progress_dto)
            
        except Exception as e:
            logger.error(f"Get upload progress failed: {e}")
            return UploadProgressResponse(
                success=False,
                errors=[Error(message=f"获取上传进度失败: {str(e)}", code="INTERNAL_ERROR")],
                data=None
            )