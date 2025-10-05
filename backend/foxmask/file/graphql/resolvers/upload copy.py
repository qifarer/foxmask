# foxmask/file/resolvers/upload_resolver.py
import strawberry
from typing import List, Optional, Dict, Any, AsyncGenerator
from strawberry.types import Info
import asyncio
import base64

from foxmask.file.graphql.schemas.upload import (
    UploadTaskType,
    UploadTaskFileType,
    UploadProgressType,
    UploadStatsType,
    UploadTaskInitInput,
    UploadTaskCompleteInput,
    UploadTaskFileChunkInput,
    UploadTaskInitResponse,
    UploadChunkResponse,
    UploadTaskCompleteResponse,
    UploadTasksType,
    MutationResponse
)
from foxmask.file.dtos.upload import (
    UploadTaskInitDTO,
    UploadTaskFileDTO,
    UploadTaskFileChunkDTO,
    UploadTaskCompleteDTO
)
from foxmask.file.services import get_service_manager
from foxmask.core.logger import logger


def get_current_user(info: Info) -> Dict[str, Any]:
    """获取当前用户信息"""
    return info.context.get("user", {})


def handle_service_exception(e: Exception, operation: str) -> str:
    """处理服务异常"""
    if isinstance(e, Exception):
        logger.warning(f"Business exception in {operation}: {str(e)}")
        return str(e)
    elif isinstance(e, Exception):
        logger.warning(f"Permission denied in {operation}: {str(e)}")
        return "无权执行此操作"
    else:
        logger.error(f"Unexpected error in {operation}: {str(e)}")
        return f"{operation}失败，请稍后重试"


@strawberry.type
class UploadQuery:    
    """上传查询Resolver - 利用MongoDB的查询能力"""
    
    @strawberry.field
    async def upload_task(self, info: Info, id: str) -> Optional[UploadTaskType]:
        """获取单个上传任务 - 直接返回MongoDB文档"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            task = await service.get_task(id, user)
            return task if task else None
        except Exception as e:
            logger.error(f"Failed to get upload task {id}: {e}")
            return None
    
    @strawberry.field
    async def upload_tasks(
        self, 
        info: Info,
        task_type: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[UploadTaskType]:
        """获取上传任务列表 - 利用MongoDB的分页和过滤能力"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            tasks = await service.list_tasks(
                user=user,
                task_type=task_type,
                source_type=source_type,
                status=status,
                created_by=created_by,
                page=page,
                page_size=page_size
            )
            return tasks
        except Exception as e:
            logger.error(f"Failed to list upload tasks: {e}")
            return []
    
    @strawberry.field
    async def upload_task_files(
        self,
        info: Info,
        task_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[UploadTaskFileType]:
        """获取任务文件列表 - 关联查询文件信息"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            files = await service.get_task_files(
                task_id, page, page_size, status, user
            )
            return files
        except Exception as e:
            logger.error(f"Failed to get task files for {task_id}: {e}")
            return []
    
    @strawberry.field
    async def upload_task_progress(self, info: Info, task_id: str) -> Optional[UploadProgressType]:
        """获取上传任务进度 - 实时计算进度信息"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            progress = await service.get_task_progress(task_id, user)
            return progress
        except Exception as e:
            logger.error(f"Failed to get progress for task {task_id}: {e}")
            return None
    
    @strawberry.field
    async def upload_stats(self, info: Info) -> UploadStatsType:
        """获取上传统计信息 - 利用MongoDB聚合查询"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            stats = await service.get_upload_stats(user)
            return stats
        except Exception as e:
            logger.error(f"Failed to get upload stats: {e}")
            # 返回空的统计信息
            return UploadStatsType(
                total_tasks=0,
                active_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                total_files_uploaded=0,
                total_data_uploaded=0,
                average_upload_speed=None
            )
    
    @strawberry.field
    async def my_recent_uploads(
        self,
        info: Info,
        limit: int = 10
    ) -> List[UploadTaskType]:
        """获取当前用户最近的上传任务"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            tasks = await service.list_tasks(
                user=user,
                created_by=user.get("user_id"),
                page=1,
                page_size=limit
            )
            return tasks
        except Exception as e:
            logger.error(f"Failed to get recent uploads: {e}")
            return []
    
    @strawberry.field
    async def upload_task_with_files(
        self,
        info: Info,
        task_id: str
    ) -> Optional[UploadTasksType]:
        """获取任务及其所有文件信息 - 一次性加载关联数据"""
        try:
            user = get_current_user(info)
            service = get_service_manager().upload_task_service
            
            # 获取任务
            task = await service.get_task(task_id, user)
            if not task:
                return None
            
            # 获取所有文件
            files = await service.get_task_files(task_id, page=1, page_size=1000, user=user)
            
            return UploadTasksType(
                task=task,
                files=files,
                total_files=len(files),
                total_size=task.total_size,
                total_chunks=sum(file.total_chunks for file in files)
            )
        except Exception as e:
            logger.error(f"Failed to get task with files {task_id}: {e}")
            return None


@strawberry.type
class UploadMutation:
    """上传变更操作Resolver - 集成MinIO存储操作"""
    
    @strawberry.mutation
    async def init_upload_task(
        self,
        info: Info,
        input: UploadTaskInitInput
    ) -> UploadTaskInitResponse:
        """统一初始化上传任务和文件信息 - 预创建MinIO上传会话"""
  
        user = "SYSTEM"#get_current_user(info)
        tenant_id = 'foxmask'
        service = get_service_manager().upload_task_service
        
        try:
            # 异步验证文件信息（不阻塞主流程）
            await self._validate_files_async(input.files)
            
            # 转换文件信息
            file_dtos = []
            for file_input in input.files:
                file_dto = UploadTaskFileDTO(
                    filename=file_input.filename,
                    original_path=file_input.original_path,
                    storage_path=file_input.storage_path,
                    file_size=file_input.file_size,
                    file_type=file_input.file_type,
                    content_type=file_input.content_type,
                    extension=file_input.extension,
                    checksum_md5=file_input.checksum_md5,
                    checksum_sha256=file_input.checksum_sha256,
                    extracted_metadata=file_input.extracted_metadata or {},
                    relative_path=file_input.relative_path
                )
                file_dtos.append(file_dto)
            
            # 创建初始化DTO
            init_dto = UploadTaskInitDTO(
                tenant_id=tenant_id,
                created_by=user,
                source_type=input.source_type,
                title=input.title,
                desc=input.desc,
                upload_strategy=input.upload_strategy,
                max_parallel_uploads=input.max_parallel_uploads,
                chunk_size=input.chunk_size,
                preserve_structure=input.preserve_structure,
                base_upload_path=input.base_upload_path,
                auto_extract_metadata=input.auto_extract_metadata,
                file_type_filters=input.file_type_filters or [],
                max_file_size=input.max_file_size,
                files=file_dtos
            )
            
            # 调用服务
            result = await service.init_upload_task(init_dto)
            
            # 构建响应
            upload_tasks = UploadTasksType(
                task=result["task"],
                files=result["files"],
                total_files=result["total_files"],
                total_size=result["total_size"],
                total_chunks=result["total_chunks"]
            )
            
            logger.info(f"Upload task initialized: {result['task'].id} with {result['total_files']} files")
            
            return UploadTaskInitResponse(
                success=True,
                message="上传任务初始化成功",
                data=upload_tasks,
                task_id=result["task"].id
            )
            
        except Exception as e:
            error_msg = handle_service_exception(e, "初始化上传任务")
            return UploadTaskInitResponse(
                success=False,
                message=error_msg
            )
    
    async def _validate_files_async(self, files: List[Any]):
        """异步验证文件信息"""
        # 这里可以添加文件验证逻辑
        # 例如：检查文件大小、类型等
        pass
    
    @strawberry.mutation
    async def upload_chunk(
        self,
        info: Info,
        input: UploadTaskFileChunkInput
    ) -> UploadChunkResponse:
        print("="*100)
        print(vars(UploadTaskFileChunkInput))
        print("upload_chunk====="*10)
        """上传文件分块 - 直接存储到MinIO"""
        user = get_current_user(info)
        tenant_id = 'foxmask'
        service = get_service_manager().upload_task_service
        
        try:
            # 限制大文件分块（保护服务器内存）
            if hasattr(input.chunk_data, 'size') and input.chunk_data.size > 100 * 1024 * 1024:  # 100MB
                return UploadChunkResponse(
                    success=False,
                    message="分块大小超过限制（最大100MB）"
                )
            
            # 读取上传的文件数据
            chunk_data = base64.b64decode(input.chunk_data)
            
            # 验证分块数据大小
            if len(chunk_data) > 100 * 1024 * 1024:  # 100MB
                return UploadChunkResponse(
                    success=False,
                    message="分块数据大小超过限制"
                )
            
            chunk_dto = UploadTaskFileChunkDTO(
                task_id=input.task_id,
                file_id=input.file_id,
                chunk_number=input.chunk_number,
                chunk_data=chunk_data,
                chunk_size=len(chunk_data),
                is_final_chunk=input.is_final_chunk,
                checksum_md5=input.checksum_md5,
                checksum_sha256=input.checksum_sha256
            )
            print("="*100)
            print(vars(UploadTaskFileChunkDTO))
            print("upload_chunk====="*10)
            
            # 调用服务上传分块
            result = await service.upload_chunk(chunk_dto)
            
            logger.info(f"Chunk uploaded: task={input.task_id}, file={input.file_id}, chunk={input.chunk_number}")
            
            return UploadChunkResponse(
                success=True,
                message="文件分块上传成功",
                file_id=result["file_id"],
                next_chunk=result["next_chunk"],
                progress=result["progress"],
                is_completed=result["is_completed"]
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "文件分块上传")
            logger.error(f"Chunk upload failed: task={input.task_id}, file={input.file_id}, chunk={input.chunk_number}, error={error_msg}")
            return UploadChunkResponse(
                success=False,
                message=error_msg
            )
    
    @strawberry.mutation
    async def complete_upload_task(
        self,
        info: Info,
        input: UploadTaskCompleteInput
    ) -> UploadTaskCompleteResponse:
        """完成上传任务 - 验证MinIO存储完整性"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            complete_dto = UploadTaskCompleteDTO(
                task_id=input.task_id,
                force_complete=input.force_complete
            )
            
            result = await service.complete_upload_task(complete_dto, user)
            
            logger.info(f"Upload task completed: {input.task_id}, completed={result['completed_files']}, failed={result['failed_files']}")
            
            return UploadTaskCompleteResponse(
                success=True,
                message="上传任务完成",
                completed_files=result["completed_files"],
                failed_files=result["failed_files"],
                total_files=result["total_files"]
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "完成上传任务")
            logger.error(f"Complete upload task failed: {input.task_id}, error={error_msg}")
            return UploadTaskCompleteResponse(
                success=False,
                message=error_msg
            )
    
    @strawberry.mutation
    async def cancel_upload_task(
        self,
        info: Info,
        task_id: str
    ) -> MutationResponse:
        """取消上传任务 - 清理MinIO中的临时文件"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            # 这里需要实现取消逻辑
            # await service.cancel_upload_task(task_id, user)
            
            logger.info(f"Upload task cancelled: {task_id}")
            
            return MutationResponse(
                success=True,
                message="上传任务已取消"
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "取消上传任务")
            return MutationResponse(
                success=False,
                message=error_msg
            )
    
    @strawberry.mutation
    async def retry_failed_files(
        self,
        info: Info,
        task_id: str,
        file_ids: Optional[List[str]] = None
    ) -> MutationResponse:
        """重试失败的文件"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            # 这里需要实现重试逻辑
            # await service.retry_failed_files(task_id, file_ids, user)
            
            logger.info(f"Retrying failed files: task={task_id}, files={file_ids}")
            
            return MutationResponse(
                success=True,
                message="失败文件重试已开始"
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "重试失败文件")
            return MutationResponse(
                success=False,
                message=error_msg
            )
    
    @strawberry.mutation
    async def cleanup_upload_task(
        self,
        info: Info,
        task_id: str
    ) -> MutationResponse:
        """清理上传任务 - 删除MinIO中的相关文件"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            # 这里需要实现清理逻辑
            # await service.cleanup_upload_task(task_id, user)
            
            logger.info(f"Upload task cleaned up: {task_id}")
            
            return MutationResponse(
                success=True,
                message="上传任务已清理"
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "清理上传任务")
            return MutationResponse(
                success=False,
                message=error_msg
            )

    @strawberry.mutation
    async def retry_failed_files(
        self,
        info: Info,
        task_id: str,
        file_ids: Optional[List[str]] = None
    ) -> MutationResponse:
        """重试失败的文件"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            await service.retry_failed_files(task_id, file_ids, user)
            
            logger.info(f"Retrying failed files: task={task_id}, files={file_ids}")
            
            return MutationResponse(
                success=True,
                message="失败文件重试已开始"
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "重试失败文件")
            return MutationResponse(
                success=False,
                message=error_msg
            )

    @strawberry.mutation
    async def cleanup_upload_task(
        self,
        info: Info,
        task_id: str
    ) -> MutationResponse:
        """清理上传任务"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        try:
            # 这里需要实现清理逻辑
            await service.cleanup_upload_task(task_id, user)
            
            logger.info(f"Upload task cleaned up: {task_id}")
            
            return MutationResponse(
                success=True,
                message="上传任务已清理"
            )
        except Exception as e:
            error_msg = handle_service_exception(e, "清理上传任务")
            return MutationResponse(
                success=False,
                message=error_msg
            )

@strawberry.type
class UploadSubscription:
    """上传订阅 - 实时监控上传进度"""
    
    @strawberry.subscription
    async def upload_progress(
        self, 
        info: Info, 
        task_id: str
    ) -> AsyncGenerator[UploadProgressType, None]:
        """订阅上传进度更新"""
        user = get_current_user(info)
        service = get_service_manager().upload_task_service
        
        last_progress = None
        check_count = 0
        max_checks = 300  # 最多检查5分钟（每秒一次）
        
        while check_count < max_checks:
            try:
                progress = await service.get_task_progress(task_id, user)
                if progress and progress != last_progress:
                    yield progress
                    last_progress = progress
                
                # 如果任务完成，停止订阅
                if progress and progress.completed_files >= progress.total_files:
                    break
                    
                check_count += 1
                await asyncio.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logger.error(f"Progress subscription error for task {task_id}: {e}")
                break