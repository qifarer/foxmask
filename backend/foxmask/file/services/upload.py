import asyncio
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from foxmask.core.config import settings
from foxmask.core.logger import logger
from foxmask.file.dtos.upload import *
from foxmask.file.models.upload import *
from foxmask.file.repositories import get_repository_manager
from foxmask.utils.helpers import (
    decode_base64_data, generate_storage_path, generate_uuid,
    get_current_timestamp, get_today_str, is_valid_base64
)
from foxmask.core.kafka import kafka_manager
from foxmask.task.message.schemas import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    MessagePriorityEnum
)
from .upload_mappers import upload_mapper


class UploadService:
    """上传任务服务实现"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
        self.task_repo = self.repo_manager.upload_task_repository
        self.file_repo = self.repo_manager.upload_task_file_repository
        self.chunk_repo = self.repo_manager.upload_task_file_chunk_repository
        self.storage_service = self.repo_manager.minio_repository
        self.event_bus = kafka_manager  # 事件总线
        self.metrics_collector = None  # 指标收集器
        
        # 进度监控缓存
        self._progress_cache: Dict[str, UploadProgressDTO] = {}
        self._file_progress_cache: Dict[str, FileUploadProgressDTO] = {}

    # ==================== 核心上传操作 ====================

    async def initialize_upload(self, input_dto: InitializeUploadInputDTO) -> InitializeUploadResponseDTO:
        """初始化上传任务"""
        try:
            # 1. 验证输入
            validation_errors = self._validate_initialize_input(input_dto)
            if validation_errors:
                return InitializeUploadResponseDTO(
                    success=False,
                    errors=validation_errors
                )

            # 2. 如果是断点续传，恢复现有任务
            if input_dto.resume_task_id:
                return await self._resume_existing_task(input_dto)
            
            # 3. 使用 Mapper 创建上传任务实体
            task_entity = upload_mapper.initialize_input_to_upload_task_entity(input_dto)
            task_entity.proc_status = UploadProcStatusEnum.PENDING
            
            # 4. 保存任务
            created_task = await self.task_repo.create(task_entity)
            
            # 5. 如果有预定义文件，创建文件记录
            if input_dto.files:
                await self._create_initial_files(created_task, input_dto.files)
           
            # 6. 使用 Mapper 转换实体为 DTO
            task_dto = await self._get_task_dto_with_files(created_task)
            
            # 7. 记录指标
            await self._record_metric("upload_tasks_initialized")

            return InitializeUploadResponseDTO(
                success=True,
                data=task_dto
            )

        except Exception as e:
            await self._record_metric("upload_tasks_failed")
            logger.error(f"初始化上传任务失败: {str(e)}")
            return InitializeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="INITIALIZATION_ERROR")]
            )
    
    async def upload_chunk(self, input_dto: UploadChunkInputDTO) -> UploadChunkResponseDTO:
        """上传文件块 - 处理 base64 字符串数据"""
        try:
            logger.info(f"=== 上传文件块开始 ===")
            logger.info(f"分块数据类型: {type(input_dto.chunk_data)}")
            logger.info(f"分块数据长度: {len(input_dto.chunk_data)}")
            logger.info(f"分块数据预览: {input_dto.chunk_data[:100]}...")
            
            # 1. 验证任务和文件存在
            task = await self.task_repo.get_by_id(input_dto.task_id)
            if not task:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="任务不存在", code="TASK_NOT_FOUND")]
                )

            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="文件不存在", code="FILE_NOT_FOUND")]
                )

            # 2. 验证和修复存储信息
            if not file_entity.minio_bucket or not file_entity.minio_object_name:
                await self._fix_missing_storage_info(file_entity, task)
                file_entity = await self.file_repo.get_by_id(input_dto.file_id)

            # 3. 生成分块对象名称
            chunk_object_name = f"{file_entity.minio_object_name}.part{input_dto.chunk_number}"

            # 4. 解码 base64 字符串为字节
            chunk_bytes = self._decode_base64_chunk_data(input_dto.chunk_data)
            if chunk_bytes is None:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="无效的base64分块数据", code="INVALID_BASE64_DATA")]
                )

            logger.info(f"解码base64数据: {len(chunk_bytes)} 字节")

            # 5. 验证块号连续性
            if not await self._validate_chunk_sequence(file_entity, input_dto.chunk_number):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="无效的分块序列", code="INVALID_CHUNK_SEQUENCE")]
                )

            # 6. 上传块到存储
            upload_result = await self.storage_service.upload_chunk(
                bucket=file_entity.minio_bucket,
                object_name=chunk_object_name,
                chunk_data=chunk_bytes,
                chunk_size=len(chunk_bytes)
            )
            
            logger.info(f"上传结果: {upload_result}")
            
            if not upload_result.get("success"):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"分块上传失败: {upload_result.get('error')}", 
                        code="CHUNK_UPLOAD_FAILED"
                    )]
                )

            # 7. 创建块记录
            chunk_entity = upload_mapper.upload_chunk_input_to_upload_task_file_chunk_entity(
                input_dto, file_entity.tenant_id
            )
            chunk_entity.minio_etag = str(upload_result.get("etag", ""))
            chunk_entity.proc_status = UploadProcStatusEnum.COMPLETED
            chunk_entity.minio_bucket = file_entity.minio_bucket
            chunk_entity.minio_object_name = chunk_object_name
            
            created_chunk = await self.chunk_repo.create(chunk_entity)

            # 8. 更新文件进度
            updated_file = await self._update_file_progress(file_entity, input_dto)

            # 9. 如果是第一个块，更新任务状态
            if input_dto.chunk_number == 1:
                await self._update_task_to_uploading(task)

            # 10. 返回响应
            chunk_dto = upload_mapper.entity_to_upload_task_file_chunk_dto(created_chunk)
            
            logger.info("=== 上传文件块成功 ===")
            
            return UploadChunkResponseDTO(
                success=True,
                data=chunk_dto
            )
        
        except Exception as e:
            logger.error(f"上传文件块失败: {str(e)}", exc_info=True)
            return UploadChunkResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="CHUNK_UPLOAD_ERROR")]
            )

    async def complete_upload(self, input_dto: CompleteUploadInputDTO) -> CompleteUploadResponseDTO:
        """完成文件上传"""
        try:
            # 1. 获取文件实体
            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="文件不存在", code="FILE_NOT_FOUND")]
                )

            # 2. 验证所有块都已上传到数据库
            if not await self._validate_all_chunks_uploaded(file_entity):
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="未上传所有分块", code="INCOMPLETE_UPLOAD")]
                )

            # 3. 验证分块在 MinIO 中存在
            merge_result = await self.storage_service.complete_multipart_upload(
                bucket=file_entity.minio_bucket,
                object_name=file_entity.minio_object_name,
                parts=await self._get_chunk_parts(file_entity.uid)
            )

            if not merge_result.get("success"):
                logger.error(f"多部分上传验证失败: {merge_result.get('error')}")
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"上传验证失败: {merge_result.get('error')}", 
                        code="UPLOAD_VERIFICATION_FAILED"
                    )]
                )

            # 4. 更新文件状态为完成
            update_dict = {
                'proc_status': UploadProcStatusEnum.COMPLETED,
                'upload_completed_at': get_current_timestamp(),
                'checksum_md5': input_dto.checksum_md5,
                'checksum_sha256': input_dto.checksum_sha256,
                'progress': 100.0,
                'updated_at': get_current_timestamp()
            }
            
            updated_file = await self.file_repo.update(file_entity.uid, update_dict)
            
            # 5. 更新任务进度
            task_entity = await self.task_repo.get_by_id(input_dto.task_id)
            task_completed = await self._update_task_progress(task_entity)
            
            #通知文件上传完成
            await self._notify_upload_completion(task_entity,file_entity)
           
            # 6. 使用 Mapper 转换响应
            file_dto = upload_mapper.entity_to_upload_task_file_dto(updated_file)
            
            logger.info(f"文件上传完成: {file_entity.filename}")
            
            return CompleteUploadResponseDTO(
                success=True,
                data=file_dto
            )

        except Exception as e:
            await self._record_metric("file_completions_failed")
            logger.error(f"完成文件上传失败: {str(e)}")
            return CompleteUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="COMPLETION_ERROR")]
            )

    async def resume_upload(self, input_dto: ResumeUploadInputDTO) -> ResumeUploadResponseDTO:
        """断点续传"""
        try:
            # 1. 获取任务
            task_entity = await self.task_repo.get_by_id(input_dto.task_id)
            if not task_entity:
                return ResumeUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="任务不存在", code="TASK_NOT_FOUND")]
                )

            # 2. 验证任务状态允许续传
            if not self._is_task_resumable(task_entity):
                return ResumeUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="任务无法恢复", code="TASK_NOT_RESUMABLE")]
                )

            # 3. 获取未完成的文件
            incomplete_files = await self.file_repo.list_by_task(
                task_entity.uid,
                tenant_id=input_dto.tenant_id,
                proc_statuses=[UploadProcStatusEnum.PENDING, UploadProcStatusEnum.UPLOADING, UploadProcStatusEnum.PROCESSING]
            )

            # 4. 为每个文件准备续传信息
            resumed_files = []
            for file_entity in incomplete_files:
                resume_info = await self._prepare_file_resume(file_entity)
                if resume_info:
                    resumed_files.append(file_entity.uid)

            # 5. 更新任务状态为 UPLOADING
            update_dict = {
                'proc_status': UploadProcStatusEnum.UPLOADING,
                'updated_at': get_current_timestamp()
            }
            await self.task_repo.update(task_entity.uid, update_dict)

            # 6. 发布事件
            

            # 7. 使用 Mapper 转换响应
            task_dto = await self._get_task_dto_with_files(task_entity)
            
            return ResumeUploadResponseDTO(
                success=True,
                data=task_dto,
                resumed_files=resumed_files,
                total_files_to_resume=len(incomplete_files)
            )

        except Exception as e:
            logger.error(f"断点续传失败: {str(e)}")
            return ResumeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="RESUME_ERROR")]
            )

    # ==================== 查询操作 ====================

    async def get_upload_task(self, task_id: str) -> GetUploadTaskResponseDTO:
        """获取上传任务详情"""
        try:
            task_entity = await self.task_repo.get_by_id(task_id)
            if not task_entity:
                return GetUploadTaskResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="任务不存在", code="TASK_NOT_FOUND")]
                )

            task_dto = await self._get_task_dto_with_files(task_entity)
            
            return GetUploadTaskResponseDTO(
                success=True,
                data=task_dto
            )
        except Exception as e:
            logger.error(f"获取上传任务失败: {str(e)}")
            return GetUploadTaskResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="FETCH_ERROR")]
            )

    async def list_upload_tasks(
        self, 
        query_dto: UploadTaskQueryDTO, 
        pagination: PaginationParams
    ) -> ListUploadTasksResponseDTO:
        """分页查询上传任务"""
        try:
            # 使用 Mapper 转换查询条件
            filter_dict = upload_mapper.upload_task_query_dto_to_filter_dict(query_dto)
            
            entities, total_count = await self.task_repo.list(
                filters=filter_dict,
                skip=(pagination.page - 1) * pagination.page_size,
                limit=pagination.page_size,
                sort_by=pagination.sort_by,
                sort_order=pagination.sort_order
            )

            # 使用 Mapper 批量转换实体为 DTO
            task_dtos = []
            for entity in entities:
                task_dto = upload_mapper.entity_to_upload_task_dto(entity, include_files=False)
                task_dtos.append(task_dto)

            # 构建分页信息
            page_info = PageInfoDTO(
                has_next_page=len(entities) == pagination.page_size,
                has_previous_page=pagination.page > 1,
                total_count=total_count,
                current_page=pagination.page,
                total_pages=(total_count + pagination.page_size - 1) // pagination.page_size if total_count else 1
            )

            return ListUploadTasksResponseDTO(
                success=True,
                data=task_dtos,
                pagination=page_info
            )
        except Exception as e:
            logger.error(f"查询上传任务列表失败: {str(e)}")
            return ListUploadTasksResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="LIST_ERROR")]
            )

    async def list_upload_task_files(
        self,
        query_dto: UploadTaskFileQueryDTO,
        pagination: PaginationParams
    ) -> ListUploadTaskFilesResponseDTO:
        """分页查询上传任务文件"""
        try:
            # 使用 Mapper 转换查询条件
            filter_dict = upload_mapper.upload_task_file_query_dto_to_filter_dict(query_dto)
            
            entities, total_count = await self.file_repo.list(
                filters=filter_dict,
                skip=(pagination.page - 1) * pagination.page_size,
                limit=pagination.page_size,
                sort_by=pagination.sort_by,
                sort_order=pagination.sort_order
            )

            # 使用 Mapper 批量转换实体为 DTO
            file_dtos = upload_mapper.entities_to_upload_task_file_dtos(entities, include_chunks=False)

            # 构建分页信息
            page_info = PageInfoDTO(
                has_next_page=len(entities) == pagination.page_size,
                has_previous_page=pagination.page > 1,
                total_count=total_count,
                current_page=pagination.page,
                total_pages=(total_count + pagination.page_size - 1) // pagination.page_size if total_count else 1
            )

            return ListUploadTaskFilesResponseDTO(
                success=True,
                data=file_dtos,
                pagination=page_info
            )
        except Exception as e:
            logger.error(f"查询上传任务文件列表失败: {str(e)}")
            return ListUploadTaskFilesResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="LIST_FILES_ERROR")]
            )

    async def get_upload_progress(self, task_id: str, tenant_id: str, include_file_details: bool = False) -> UploadProgressDTO:
        """获取上传进度"""
        try:
            task_entity = await self.task_repo.get_by_id(task_id)
            if not task_entity:
                return None

            # 使用 Mapper 转换进度信息
            progress_dto = upload_mapper.entity_to_upload_progress_dto(task_entity)
            
            if include_file_details and progress_dto:
                # 获取处理中的文件
                processing_files = await self.file_repo.list_by_task(
                    task_id, tenant_id, proc_status=UploadProcStatusEnum.UPLOADING
                )
                
                file_progress_dtos = []
                for file_entity in processing_files:
                    file_progress = upload_mapper.entity_to_file_upload_progress_dto(file_entity)
                    if file_progress:
                        file_progress_dtos.append(file_progress)
                
                progress_dto.current_uploading_files = file_progress_dtos

            return progress_dto

        except Exception as e:
            logger.error(f"获取上传进度失败: {str(e)}")
            return None

    # ==================== 辅助方法 ====================

    def _decode_base64_chunk_data(self, chunk_data: str) -> Optional[bytes]:
        """解码 base64 字符串为字节"""
        try:
            logger.info("验证base64数据...")
            
            if not is_valid_base64(chunk_data):
                logger.error("无效的base64数据格式")
                return None
            
            decoded_data = decode_base64_data(chunk_data)
            if decoded_data:
                logger.info(f"Base64解码成功: {len(decoded_data)} 字节")
                return decoded_data
            else:
                logger.error("Base64解码失败")
                return None
                
        except Exception as e:
            logger.error(f"Base64处理失败: {e}")
            return None

    async def _update_file_progress(self, file_entity, input_dto: UploadChunkInputDTO):
        """更新文件进度 - 确保状态正确流转"""
        uploaded_chunks = await self.chunk_repo.count_by_file(file_entity.uid)
        progress = (uploaded_chunks / file_entity.total_chunks) * 100.0
        
        # 文件状态从 PENDING 变为 UPLOADING
        update_dict = {
            'uploaded_chunks': uploaded_chunks,
            'current_chunk': input_dto.chunk_number,
            'progress': progress,
            'proc_status': UploadProcStatusEnum.UPLOADING,
            'updated_at': get_current_timestamp()
        }
        
        # 如果是第一次上传块，设置开始时间
        if uploaded_chunks == 1 and not file_entity.upload_started_at:
            update_dict['upload_started_at'] = get_current_timestamp()
            
        return await self.file_repo.update(file_entity.uid, update_dict)

    async def _update_task_to_uploading(self, task_entity):
        """将任务状态从 PENDING 更新为 UPLOADING"""
        if task_entity.proc_status == UploadProcStatusEnum.PENDING:
            update_dict = {
                'proc_status': UploadProcStatusEnum.UPLOADING,
                'updated_at': get_current_timestamp()
            }
            await self.task_repo.update(task_entity.uid, update_dict)

    async def _update_task_progress(self, task_entity: UploadTask) -> bool:
        """更新任务进度"""
        try:
            # 获取文件统计信息
            file_stats = await self.file_repo.get_stats_by_task(task_entity.uid)
            
            # 创建更新数据
            update_data = {
                'total_files': file_stats["total_files"],
                'completed_files': file_stats["completed_files"],
                'failed_files': file_stats["failed_files"],
                'processing_files': file_stats["processing_files"],
                'total_size': file_stats["total_size"],
                'uploaded_size': file_stats["uploaded_size"],
                'updated_at': get_current_timestamp()
            }
            
            # 计算进度百分比
            if file_stats["total_size"] > 0:
                progress_percentage = (file_stats["uploaded_size"] / file_stats["total_size"]) * 100
            else:
                progress_percentage = 0.0
            
            # 更新任务状态
            if file_stats["completed_files"] == file_stats["total_files"] and file_stats["total_files"] > 0:
                update_data['proc_status'] = UploadProcStatusEnum.COMPLETED
            elif file_stats["failed_files"] > 0:
                update_data['proc_status'] = UploadProcStatusEnum.FAILED
            else:
                update_data['proc_status'] = UploadProcStatusEnum.UPLOADING
            
            await self.task_repo.update(task_entity.uid, update_data)
            
            logger.info(f"更新任务进度: {task_entity.uid}, 进度: {progress_percentage:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")
            return False

    async def _create_initial_files(self, task_entity: UploadTask, files: List[InitializeUploadFileInputDTO]):
        """创建初始文件记录"""
        file_entities = []
        
        for file_input in files:
            file_id = generate_uuid()
            # 生成存储路径和对象名称
            storage_path = generate_storage_path(access="private",
                                                 base_path=task_entity.base_upload_path, 
                                                 tenant_id=task_entity.tenant_id,
                                                 file_name=f"{file_id}{file_input.extension}",
            )
            object_name = storage_path
            minio_bucket = settings.MINIO_BUCKET_NAME if not task_entity.tenant_id else task_entity.tenant_id
            
            # 使用 Mapper 创建文件实体
            file_entity = upload_mapper.initialize_file_input_to_upload_task_file_entity(
                file_input, task_entity.uid, task_entity.tenant_id, file_id, storage_path=storage_path
            )            
            # 设置存储信息
            file_entity.minio_bucket = minio_bucket
            file_entity.minio_object_name = object_name
            file_entity.storage_path = storage_path
            file_entity.proc_status = UploadProcStatusEnum.PENDING
            
            file_entities.append(file_entity)

        # 批量创建文件
        if file_entities:
            await self.file_repo.bulk_create(file_entities)

    def _validate_initialize_input(self, input_dto: InitializeUploadInputDTO) -> List[ErrorDTO]:
        """验证初始化输入"""
        errors = []
        
        if not input_dto.title or len(input_dto.title.strip()) == 0:
            errors.append(ErrorDTO(message="标题必填", code="MISSING_TITLE"))
            
        if not input_dto.source_paths:
            errors.append(ErrorDTO(message="源路径必填", code="MISSING_SOURCE_PATHS"))
            
        if input_dto.chunk_size <= 0:
            errors.append(ErrorDTO(message="分块大小必须为正数", code="INVALID_CHUNK_SIZE"))
            
        if input_dto.max_parallel_uploads <= 0:
            errors.append(ErrorDTO(message="最大并行上传数必须为正数", code="INVALID_PARALLEL_UPLOADS"))
            
        return errors

    async def _resume_existing_task(self, input_dto: InitializeUploadInputDTO) -> InitializeUploadResponseDTO:
        """恢复现有任务"""
        existing_task = await self.task_repo.get_by_id(input_dto.resume_task_id)
        if not existing_task:
            return InitializeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message="恢复任务不存在", code="RESUME_TASK_NOT_FOUND")]
            )

        # 使用 Mapper 创建更新字典
        update_dict = {
            'title': input_dto.title,
            'desc': input_dto.desc,
            'proc_status': UploadProcStatusEnum.UPLOADING,
            'updated_at': get_current_timestamp()
        }
        
        updated_task = await self.task_repo.update(existing_task.uid, update_dict)
        task_dto = await self._get_task_dto_with_files(updated_task)
        
        return InitializeUploadResponseDTO(
            success=True,
            data=task_dto
        )

    async def _validate_chunk_sequence(self, file_entity, chunk_number: int) -> bool:
        """验证块号连续性"""
        # 检查是否重复上传
        existing_chunk = await self.chunk_repo.get_by_file_and_number(
            file_entity.uid, chunk_number
        )
        if existing_chunk:
            return False
            
        # 检查是否跳跃上传（对于顺序上传策略）
        if chunk_number > 1:
            previous_chunk = await self.chunk_repo.get_by_file_and_number(
                file_entity.uid, chunk_number - 1
            )
            if not previous_chunk:
                return False
                
        return True

    async def _validate_all_chunks_uploaded(self, file_entity) -> bool:
        """验证所有块都已上传"""
        try:
            uploaded_count = await self.chunk_repo.count_by_file(file_entity.uid)
            total_chunks = file_entity.total_chunks
            
            logger.info(f"分块验证: 已上传={uploaded_count}, 总计={total_chunks}, 文件={file_entity.filename}")
            
            # 获取所有分块详情
            chunks = await self.chunk_repo.list_by_file(file_entity.uid)
            for chunk in chunks:
                logger.info(f"分块 {chunk.chunk_number}: {chunk.minio_object_name}, 状态: {chunk.proc_status}")
            
            return uploaded_count == total_chunks
        except Exception as e:
            logger.error(f"分块验证失败: {e}")
            return False

    async def _get_chunk_parts(self, file_id: str) -> List[Dict]:
        """获取块部件列表用于合并"""
        chunks = await self.chunk_repo.list_by_file(file_id)
        return [
            {
                "part_number": chunk.chunk_number,
                "etag": chunk.minio_etag,
            }
            for chunk in chunks
        ]

    def _is_task_resumable(self, task_entity) -> bool:
        """检查任务是否可恢复"""
        resumable_statuses = [
            UploadProcStatusEnum.PENDING,
            UploadProcStatusEnum.UPLOADING,
            UploadProcStatusEnum.FAILED
        ]
        return task_entity.proc_status in resumable_statuses

    async def _prepare_file_resume(self, file_entity) -> Optional[UploadResumeInfoDTO]:
        """准备文件续传信息"""
        uploaded_chunks = await self.chunk_repo.count_by_file(file_entity.uid)
        
        if uploaded_chunks >= file_entity.total_chunks:
            return None  # 文件已经上传完成
            
        # 使用 Mapper 转换续传信息
        resume_info = upload_mapper.entity_to_upload_resume_info_dto(file_entity)
        if resume_info:
            resume_info.uploaded_chunks = uploaded_chunks
            resume_info.next_chunk_number = uploaded_chunks + 1
            
        return resume_info

    async def _get_task_dto_with_files(self, task_entity) -> UploadTaskDTO:
        """获取包含文件列表的任务 DTO"""
        # 获取任务关联的文件
        files = await self.file_repo.list_by_task(task_entity.uid, task_entity.tenant_id)
        
        # 使用 Mapper 转换任务实体和文件实体
        task_dto = upload_mapper.entity_to_upload_task_dto(task_entity, include_files=False)
        
        if files:
            file_dtos = upload_mapper.entities_to_upload_task_file_dtos(files, include_chunks=False)
            task_dto.files = file_dtos
            
        return task_dto

    async def _record_metric(self, metric_name: str, value: float = 1.0):
        """记录指标"""
        if self.metrics_collector:
            try:
                await self.metrics_collector.increment_counter(metric_name, value)
            except Exception as e:
                logger.warning(f"记录指标失败 {metric_name}: {str(e)}")
   
    async def _fix_missing_storage_info(self, file_entity: UploadTaskFile, task_entity: UploadTask):
        """修复缺失的存储信息"""
        # 生成存储路径和对象名称
        storage_path = generate_storage_path(access="private",
                                            base_path=task_entity.base_upload_path, 
                                            tenant_id=task_entity.tenant_id,
                                            file_name=f"{file_entity.uid}{file_entity.extension}")
         
        object_name = storage_path
        
        update_data = {
            'storage_path': storage_path,
            'minio_bucket': settings.MINIO_BUCKET_NAME,
            'minio_object_name': object_name,
            'updated_at': get_current_timestamp()
        }
        
        await self.file_repo.update(file_entity.uid, update_data)
        logger.info(f"修复缺失的存储信息: {file_entity.uid}")


    async def _validate_file_integrity(self, file_entity: UploadTaskFile, input_dto: CompleteUploadInputDTO) -> bool:
        """验证文件完整性"""
        try:
            # 如果提供了校验和，进行验证
            if input_dto.checksum_md5 or input_dto.checksum_sha256:
                # 从存储下载文件进行校验
                file_data = await self.storage_service.download_chunk(
                    file_entity.minio_bucket,
                    file_entity.minio_object_name
                )
                
                if input_dto.checksum_md5:
                    import hashlib
                    calculated_md5 = hashlib.md5(file_data).hexdigest()
                    if calculated_md5 != input_dto.checksum_md5:
                        logger.error(f"MD5校验失败: 期望={input_dto.checksum_md5}, 实际={calculated_md5}")
                        return False
                
                if input_dto.checksum_sha256:
                    import hashlib
                    calculated_sha256 = hashlib.sha256(file_data).hexdigest()
                    if calculated_sha256 != input_dto.checksum_sha256:
                        logger.error(f"SHA256校验失败: 期望={input_dto.checksum_sha256}, 实际={calculated_sha256}")
                        return False
            
            logger.info(f"文件完整性验证通过: {file_entity.filename}")
            return True
            
        except Exception as e:
            logger.error(f"文件完整性验证失败: {e}")
            return False

    async def _mark_file_as_processing(self, file_entity: UploadTaskFile):
        """标记文件为处理状态"""
        try:
            update_dict = {
                'proc_status': UploadProcStatusEnum.PROCESSING,
                'updated_at': get_current_timestamp()
            }
            await self.file_repo.update(file_entity.uid, update_dict)
            logger.info(f"文件标记为处理状态: {file_entity.filename}")
            
        except Exception as e:
            logger.error(f"标记文件为处理状态失败: {e}")

    async def _cleanup_failed_upload(self, task_id: str, file_id: str):
        """清理失败的上传"""
        try:
            # 删除文件记录
            await self.file_repo.delete(file_id)
            
            # 删除相关的分块记录
            chunks = await self.chunk_repo.list_by_file(file_id)
            for chunk in chunks:
                await self.chunk_repo.delete(chunk.uid)
                
            # 清理存储中的分块文件
            file_entity = await self.file_repo.get_by_id(file_id)
            if file_entity:
                await self.storage_service.cleanup_chunks(
                    file_entity.minio_bucket,
                    f"{file_entity.minio_object_name}.part"
                )
            
            logger.info(f"清理失败的上传: 任务={task_id}, 文件={file_id}")
            
        except Exception as e:
            logger.error(f"清理失败的上传时出错: {e}")

    async def _update_task_metrics(self, task_entity: UploadTask):
        """更新任务指标"""
        try:
            # 计算各种指标
            total_files = task_entity.total_files or 0
            completed_files = task_entity.completed_files or 0
            failed_files = task_entity.failed_files or 0
            processing_files = task_entity.processing_files or 0
            
            # 记录指标
            await self._record_metric("upload_task_total_files", total_files)
            await self._record_metric("upload_task_completed_files", completed_files)
            await self._record_metric("upload_task_failed_files", failed_files)
            await self._record_metric("upload_task_processing_files", processing_files)
            
            # 计算成功率
            if total_files > 0:
                success_rate = (completed_files / total_files) * 100
                await self._record_metric("upload_task_success_rate", success_rate)
            
            logger.debug(f"更新任务指标: 任务={task_entity.uid}, 完成={completed_files}/{total_files}")
            
        except Exception as e:
            logger.error(f"更新任务指标失败: {e}")

    async def _notify_upload_completion(self, task_entity: UploadTask, file_entity: UploadTaskFile):
        """通知上传完成"""
        try:
            if self.event_bus:
                event_data = {
                    "type": MessageEventTypeEnum.CREATE_FILE_FROM_UPLOAD,
                    "file_id": file_entity.uid,
                    "tenant": task_entity.tenant_id,
                    "user": task_entity.created_by,
                    "filename": file_entity.filename,
                    "priority": MessagePriorityEnum.NORMAL
                }
                await self.event_bus.send_message(
                    topic=MessageTopicEnum.KB_PROCESSING,
                    value=event_data,
                    key=file_entity.uid)
         
                logger.info(f"发送文件上传完成通知: {file_entity.filename}")
                
        except Exception as e:
            logger.error(f"发送上传完成通知失败: {e}")

    async def _handle_upload_error(self, task_id: str, file_id: str, error: Exception):
        """处理上传错误"""
        try:
            # 更新文件状态为失败
            await self.file_repo.update_file_status(
                file_id,
                UploadProcStatusEnum.FAILED,
                error_info={"error": str(error), "timestamp": get_current_timestamp()}
            )
            
            # 更新任务进度
            task_entity = await self.task_repo.get_by_id(task_id)
            if task_entity:
                await self._update_task_progress(task_entity)
            
            # 记录错误指标
            await self._record_metric("upload_errors")
            
            logger.error(f"处理上传错误: 任务={task_id}, 文件={file_id}, 错误={error}")
            
        except Exception as e:
            logger.error(f"处理上传错误时发生异常: {e}")

    async def _validate_storage_availability(self, bucket: str) -> bool:
        """验证存储可用性"""
        try:
            # 检查存储桶是否存在
            await self.storage_service._ensure_bucket_exists(bucket)
            
            # 尝试创建一个测试对象并删除
            test_object_name = f"healthcheck-{generate_uuid()}"
            test_data = b"healthcheck"
            
            upload_result = await self.storage_service.upload_chunk(
                bucket=bucket,
                object_name=test_object_name,
                chunk_data=test_data
            )
            
            if upload_result.get("success"):
                # 清理测试对象
                await self.storage_service.delete_chunk(bucket, test_object_name)
                return True
            else:
                logger.error(f"存储可用性检查失败: {upload_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"存储可用性检查异常: {e}")
            return False

upload_service = UploadService()            