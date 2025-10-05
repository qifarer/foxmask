import asyncio, re, os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from foxmask.file.dtos.upload import *
from foxmask.file.models.upload import *
from foxmask.file.repositories import get_repository_manager
from foxmask.utils.helpers import generate_uuid, get_current_timestamp,is_valid_base64,decode_base64_data
from foxmask.core.config import settings
from foxmask.core.logger import logger

from .upload_mappers import upload_mapper

class UploadService:
    """上传任务服务实现"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
        self.task_repo = self.repo_manager.upload_task_repository
        self.file_repo = self.repo_manager.upload_task_file_repository
        self.chunk_repo = self.repo_manager.upload_task_file_chunk_repository
        self.storage_service = self.repo_manager.minio_repository
        self.event_bus = None  # event_bus
        self.metrics_collector = None  # metrics_collector
        
        # 进度监控缓存
        self._progress_cache: Dict[str, UploadProgressDTO] = {}
        self._file_progress_cache: Dict[str, FileUploadProgressDTO] = {}

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
            
            # 3. 使用 Mapper 创建上传任务实体 - 初始状态为 PENDING
            task_entity = upload_mapper.initialize_input_to_upload_task_entity(input_dto)
            task_entity.proc_status = UploadProcStatusEnum.PENDING  # 明确设置任务状态为待处理
            
            # 4. 保存任务
            created_task = await self.task_repo.create(task_entity)
            
            # 5. 如果有预定义文件，创建文件记录 - 文件初始状态为 PENDING
            if input_dto.files:
                await self._create_initial_files(created_task, input_dto.files, input_dto.tenant_id)
           
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
            logger.error(f"Initialize upload failed: {str(e)}")
            return InitializeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="INITIALIZATION_ERROR")]
            )
    
    async def upload_chunk(self, input_dto: UploadChunkInputDTO) -> UploadChunkResponseDTO:
        """上传文件块 - 处理 base64 字符串数据"""
        try:
            logger.info(f"=== UPLOAD CHUNK START ===")
            logger.info(f"Chunk data type: {type(input_dto.chunk_data)}")
            logger.info(f"Chunk data length: {len(input_dto.chunk_data)}")
            logger.info(f"Chunk data preview: {input_dto.chunk_data[:100]}...")
            
            # 1. 验证任务和文件存在
            task = await self.task_repo.get_by_id(input_dto.task_id)
            if not task:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Task not found", code="TASK_NOT_FOUND")]
                )

            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File not found", code="FILE_NOT_FOUND")]
                )

            # 2. 验证和修复存储信息
            if not file_entity.minio_bucket or not file_entity.minio_object_name:
                await self._fix_missing_storage_info(file_entity, task)
                file_entity = await self.file_repo.get_by_id(input_dto.file_id)

            # 3. 生成分块对象名称
            chunk_object_name = f"{file_entity.minio_object_name}.part{input_dto.chunk_number}"

            # 4. ✅ 修复：解码 base64 字符串为字节
            chunk_bytes = self._decode_base64_chunk_data(input_dto.chunk_data)
            if chunk_bytes is None:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Invalid base64 chunk data", code="INVALID_BASE64_DATA")]
                )

            logger.info(f"Decoded base64 data: {len(chunk_bytes)} bytes")

            # 5. 验证块号连续性
            if not await self._validate_chunk_sequence(file_entity, input_dto.chunk_number):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Invalid chunk sequence", code="INVALID_CHUNK_SEQUENCE")]
                )

            # 6. 上传块到存储
            upload_result = await self.storage_service.upload_chunk(
                bucket=file_entity.minio_bucket,
                object_name=chunk_object_name,
                chunk_data=chunk_bytes,  # ✅ 使用解码后的字节数据
                chunk_size=len(chunk_bytes)
            )
            
            logger.info(f"Upload result: {upload_result}")
            
            if not upload_result.get("success"):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Chunk upload failed: {upload_result.get('error')}", 
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
            
            logger.info("=== UPLOAD CHUNK SUCCESS ===")
            
            return UploadChunkResponseDTO(
                success=True,
                data=chunk_dto
            )
        
        except Exception as e:
            logger.error(f"Upload chunk failed: {str(e)}", exc_info=True)
            return UploadChunkResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="CHUNK_UPLOAD_ERROR")]
            )

    def _decode_base64_chunk_data(self, chunk_data: str) -> Optional[bytes]:
        """解码 base64 字符串为字节"""
        try:
            
            logger.info("Validating base64 data...")
            
            if not is_valid_base64(chunk_data):
                logger.error("Invalid base64 data format")
                return None
            
            decoded_data = decode_base64_data(chunk_data)
            if decoded_data:
                logger.info(f"Base64 decoding successful: {len(decoded_data)} bytes")
                return decoded_data
            else:
                logger.error("Base64 decoding failed")
                return None
                
        except Exception as e:
            logger.error(f"Base64 processing failed: {e}")
            return None
        
    async def upload_chunk_2(self, input_dto: UploadChunkInputDTO) -> UploadChunkResponseDTO:
        """上传文件块 - 添加详细调试信息"""
        try:
            # 1. 验证任务和文件存在
            task = await self.task_repo.get_by_id(input_dto.task_id)
            if not task:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Task not found", code="TASK_NOT_FOUND")]
                )

            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File not found", code="FILE_NOT_FOUND")]
                )

            # 2. 验证和修复存储信息
            if not file_entity.minio_bucket or not file_entity.minio_object_name:
                await self._fix_missing_storage_info(file_entity, task)
                file_entity = await self.file_repo.get_by_id(input_dto.file_id)

            # 3. 生成分块对象名称
            chunk_object_name = f"{file_entity.minio_object_name}.part{input_dto.chunk_number}"
            
            # ✅ 添加详细的调试信息
            logger.info(f"=== UPLOAD CHUNK DEBUG ===")
            logger.info(f"File: {file_entity.filename}")
            logger.info(f"File ID: {file_entity.uid}")
            logger.info(f"Chunk number: {input_dto.chunk_number}")
            logger.info(f"Chunk data size: {len(input_dto.chunk_data)} bytes")
            logger.info(f"Bucket: {file_entity.minio_bucket}")
            logger.info(f"Base object name: {file_entity.minio_object_name}")
            logger.info(f"Chunk object name: {chunk_object_name}")
            logger.info(f"=== END DEBUG ===")

            # 4. 验证块号连续性
            if not await self._validate_chunk_sequence(file_entity, input_dto.chunk_number):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Invalid chunk sequence", code="INVALID_CHUNK_SEQUENCE")]
                )

            # 5. 上传块到存储
            logger.info(f"Calling storage_service.upload_chunk...")
            upload_result = await self.storage_service.upload_chunk(
                bucket=file_entity.minio_bucket,
                object_name=chunk_object_name,
                chunk_data=input_dto.chunk_data,
                chunk_size=len(input_dto.chunk_data)
            )
            
            logger.info(f"Upload result: {upload_result}")
            
            if not upload_result.get("success"):
                logger.error(f"Chunk upload failed: {upload_result}")
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Chunk upload failed: {upload_result.get('error')}", 
                        code="CHUNK_UPLOAD_FAILED"
                    )]
                )

            # 6. 创建块记录
            chunk_entity = upload_mapper.upload_chunk_input_to_upload_task_file_chunk_entity(
                input_dto, file_entity.tenant_id
            )
            chunk_entity.minio_etag = str(upload_result.get("etag", ""))
            chunk_entity.proc_status = UploadProcStatusEnum.COMPLETED
            chunk_entity.minio_bucket = file_entity.minio_bucket
            chunk_entity.minio_object_name = chunk_object_name
            
            created_chunk = await self.chunk_repo.create(chunk_entity)
            logger.info(f"Chunk record created: {created_chunk.uid}")

            # 7. 更新文件进度
            updated_file = await self._update_file_progress(file_entity, input_dto)
            logger.info(f"File progress updated: {updated_file.progress}%")

            # 8. 如果是第一个块，更新任务状态
            if input_dto.chunk_number == 1:
                await self._update_task_to_uploading(task)
                logger.info("Task status updated to UPLOADING")

            # 9. 返回响应
            chunk_dto = upload_mapper.entity_to_upload_task_file_chunk_dto(created_chunk)
            
            return UploadChunkResponseDTO(
                success=True,
                data=chunk_dto
            )
        
        except Exception as e:
            await self._record_metric("chunk_uploads_failed")
            logger.error(f"Upload chunk failed: {str(e)}", exc_info=True)
            return UploadChunkResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="CHUNK_UPLOAD_ERROR")]
            )
        
    async def upload_chunk_1(self, input_dto: UploadChunkInputDTO) -> UploadChunkResponseDTO:
        """上传文件块"""
        try:
            # 1. 验证任务和文件存在
            task = await self.task_repo.get_by_id(input_dto.task_id)
            if not task:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Task not found", code="TASK_NOT_FOUND")]
                )

            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File not found", code="FILE_NOT_FOUND")]
                )

            # 检查任务状态是否允许上传
            if task.proc_status not in [UploadProcStatusEnum.PENDING, UploadProcStatusEnum.UPLOADING]:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Cannot upload chunk for task with status: {task.proc_status.value}",
                        code="INVALID_TASK_STATUS"
                    )]
                )

            # 检查文件状态是否允许上传
            if file_entity.proc_status not in [UploadProcStatusEnum.PENDING, UploadProcStatusEnum.UPLOADING]:
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Cannot upload chunk for file with status: {file_entity.proc_status.value}",
                        code="INVALID_FILE_STATUS"
                    )]
                )
             # 2. 验证和修复存储信息
            if not file_entity.minio_bucket or not file_entity.minio_object_name:
                # 如果存储信息缺失，重新生成
                await self._fix_missing_storage_info(file_entity, task)
                # 重新获取修复后的文件实体
                file_entity = await self.file_repo.get_by_id(input_dto.file_id)

            # 3. 使用文件的存储信息，而不是输入DTO中的信息（确保一致性）
            input_dto.minio_bucket = file_entity.minio_bucket
            input_dto.minio_object_name = f"{file_entity.minio_object_name}.part{input_dto.chunk_number}"

            # 2. 验证块号连续性
            if not await self._validate_chunk_sequence(file_entity, input_dto.chunk_number):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Invalid chunk sequence", code="INVALID_CHUNK_SEQUENCE")]
                )

            # 3. 上传块到存储
            upload_result = await self.storage_service.upload_chunk(
                bucket=input_dto.minio_bucket,
                object_name=input_dto.minio_object_name,
                chunk_data=input_dto.chunk_data,
                chunk_size=input_dto.chunk_size
            )
            
            print(f"====upload_chunk====:upload_result:{str(upload_result)}")
            if not upload_result.get("success"):
                return UploadChunkResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Chunk upload failed", code="CHUNK_UPLOAD_FAILED")]
                )

            # 4. 使用 Mapper 创建块记录
            chunk_entity = upload_mapper.upload_chunk_input_to_upload_task_file_chunk_entity(
                input_dto, file_entity.tenant_id
            )
            chunk_entity.minio_etag = str(upload_result.get("etag"))
            chunk_entity.proc_status = UploadProcStatusEnum.COMPLETED
            
            created_chunk = await self.chunk_repo.create(chunk_entity)

            # 5. 更新文件进度 - 文件状态变为 UPLOADING
            updated_file = await self._update_file_progress(file_entity, input_dto)

            # 6. 如果是第一个块，将任务状态从 PENDING 变为 UPLOADING
            if input_dto.chunk_number == 1:
                await self._update_task_to_uploading(task)

            # 7. 检查文件是否已完成所有块上传
            file_completed = False
            if input_dto.is_final_chunk:
                # 验证所有块是否都已上传
                all_chunks_uploaded = await self._validate_all_chunks_uploaded(updated_file)
                if all_chunks_uploaded:
                    # 文件已完成所有块上传，标记为处理状态
                    await self._mark_file_as_processing(updated_file)
                    file_completed = True

            # 8. 更新任务进度并检查任务是否完成
            task_completed = await self._update_task_progress(task)

            # 10. 使用 Mapper 转换响应
            chunk_dto = upload_mapper.entity_to_upload_task_file_chunk_dto(created_chunk)
            
            return UploadChunkResponseDTO(
                success=True,
                data=chunk_dto
            )
        
        except Exception as e:
            await self._record_metric("chunk_uploads_failed")
            logger.error(f"Upload chunk failed: {str(e)}", exc_info=True)
            return UploadChunkResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="CHUNK_UPLOAD_ERROR")]
            )

    async def complete_upload(self, input_dto: CompleteUploadInputDTO) -> CompleteUploadResponseDTO:
        """完成文件上传 - 修复合并逻辑"""
        try:
            # 1. 获取文件实体
            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File not found", code="FILE_NOT_FOUND")]
                )

            # 2. 验证所有块都已上传到数据库
            if not await self._validate_all_chunks_uploaded(file_entity):
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Not all chunks uploaded", code="INCOMPLETE_UPLOAD")]
                )

            # 3. ✅ 简化：只验证分块在 MinIO 中存在，不进行物理合并
            merge_result = await self.storage_service.complete_multipart_upload(
                bucket=file_entity.minio_bucket,
                object_name=file_entity.minio_object_name,
                parts=await self._get_chunk_parts(file_entity.uid)
            )

            if not merge_result.get("success"):
                logger.error(f"Multipart upload verification failed: {merge_result.get('error')}")
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Upload verification failed: {merge_result.get('error')}", 
                        code="UPLOAD_VERIFICATION_FAILED"
                    )]
                )

            # 4. 验证文件完整性（可选）
            # 这里可以添加 MD5/SHA256 校验

            # 5. 更新文件状态为完成
            update_dict = {
                'proc_status': UploadProcStatusEnum.COMPLETED,
                'upload_completed_at': get_current_timestamp(),
                'checksum_md5': input_dto.checksum_md5,
                'checksum_sha256': input_dto.checksum_sha256,
                'progress': 100.0,
                'updated_at': get_current_timestamp()
            }
            
            updated_file = await self.file_repo.update(file_entity.uid, update_dict)

            # 6. 更新任务进度
            task_entity = await self.task_repo.get_by_id(input_dto.task_id)
            task_completed = await self._update_task_progress(task_entity)

            # 7. 使用 Mapper 转换响应
            file_dto = upload_mapper.entity_to_upload_task_file_dto(updated_file)
            
            logger.info(f"File upload completed successfully: {file_entity.filename}")
            
            return CompleteUploadResponseDTO(
                success=True,
                data=file_dto
            )

        except Exception as e:
            await self._record_metric("file_completions_failed")
            logger.error(f"Complete upload failed: {str(e)}", exc_info=True)
            return CompleteUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="COMPLETION_ERROR")]
            )
        
    async def complete_upload_2(self, input_dto: CompleteUploadInputDTO) -> CompleteUploadResponseDTO:
        """完成文件上传"""
        try:
            # 1. 获取文件实体
            file_entity = await self.file_repo.get_by_id(input_dto.file_id)
            if not file_entity:
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File not found", code="FILE_NOT_FOUND")]
                )

            # 检查文件状态是否允许完成 - 只有 PROCESSING 状态的文件才能完成
            if file_entity.proc_status != UploadProcStatusEnum.PROCESSING:
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(
                        message=f"Cannot complete file with status: {file_entity.proc_status.value}. Expected: PROCESSING",
                        code="INVALID_FILE_STATUS"
                    )]
                )

            # 2. 验证所有块都已上传
            if not await self._validate_all_chunks_uploaded(file_entity):
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Not all chunks uploaded", code="INCOMPLETE_UPLOAD")]
                )

            # 3. 合并文件块（如果存储服务需要）
            merge_result = await self.storage_service.complete_multipart_upload(
                bucket=file_entity.minio_bucket,
                object_name=file_entity.minio_object_name,
                parts=await self._get_chunk_parts(file_entity.uid)
            )

            if not merge_result.get("success"):
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File merge failed", code="FILE_MERGE_FAILED")]
                )

            # 4. 验证文件完整性
            if not await self._validate_file_integrity(file_entity, input_dto):
                return CompleteUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="File integrity check failed", code="INTEGRITY_CHECK_FAILED")]
                )

            # 5. 更新文件状态为完成 - 文件状态从 PROCESSING 变为 COMPLETED
            update_dict = {
                'proc_status': UploadProcStatusEnum.COMPLETED,
                'upload_completed_at': get_current_timestamp(),
                'checksum_md5': input_dto.checksum_md5,
                'checksum_sha256': input_dto.checksum_sha256,
                'progress': 100.0,
                'updated_at': get_current_timestamp()
            }
            
            updated_file = await self.file_repo.update(file_entity.uid, update_dict)

            # 6. 更新任务进度并检查任务是否完成
            task_entity = await self.task_repo.get_by_id(input_dto.task_id)
            task_completed = await self._update_task_progress(task_entity)

            # 如果任务完成，发布任务完成事件
            if task_completed:
                await self._publish_event("task.completed", {
                    "task_id": input_dto.task_id,
                    "total_files": task_entity.total_files,
                    "completed_files": task_entity.completed_files + 1,  # +1 因为刚完成这个文件
                    "failed_files": task_entity.failed_files,
                    "task_status": task_entity.proc_status.value
                })

            # 8. 使用 Mapper 转换响应
            file_dto = upload_mapper.entity_to_upload_task_file_dto(updated_file)
            
            return CompleteUploadResponseDTO(
                success=True,
                data=file_dto
            )

        except Exception as e:
            await self._record_metric("file_completions_failed")
            logger.error(f"Complete upload failed: {str(e)}", exc_info=True)
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
                    errors=[ErrorDTO(message="Task not found", code="TASK_NOT_FOUND")]
                )

            # 2. 验证任务状态允许续传
            if not self._is_task_resumable(task_entity):
                return ResumeUploadResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Task cannot be resumed", code="TASK_NOT_RESUMABLE")]
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
            await self._publish_event("upload.resumed", {
                "task_id": input_dto.task_id,
                "resumed_files": len(resumed_files),
                "total_files": len(incomplete_files),
                "task_status": UploadProcStatusEnum.UPLOADING.value
            })

            # 7. 使用 Mapper 转换响应
            task_dto = await self._get_task_dto_with_files(task_entity)
            
            return ResumeUploadResponseDTO(
                success=True,
                data=task_dto,
                resumed_files=resumed_files,
                total_files_to_resume=len(incomplete_files)
            )

        except Exception as e:
            logger.error(f"Resume upload failed: {str(e)}")
            return ResumeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message=str(e), code="RESUME_ERROR")]
            )

    # ==================== 修正的辅助方法 ====================

    async def _update_file_progress(self, file_entity, input_dto: UploadChunkInputDTO):
        """更新文件进度 - 确保状态正确流转"""
        uploaded_chunks = await self.chunk_repo.count_by_file(file_entity.uid)
        progress = (uploaded_chunks / file_entity.total_chunks) * 100.0
        
        # 文件状态从 PENDING 变为 UPLOADING
        update_dict = {
            'uploaded_chunks': uploaded_chunks,
            'current_chunk': input_dto.chunk_number,
            'progress': progress,
            'proc_status': UploadProcStatusEnum.UPLOADING,  # 确保状态为 UPLOADING
            'updated_at': get_current_timestamp()
        }
        
        # 如果是第一次上传块，设置开始时间
        if uploaded_chunks == 1 and not file_entity.upload_started_at:
            update_dict['upload_started_at'] = get_current_timestamp()
            
        return await self.file_repo.update(file_entity.uid, update_dict)

    async def _mark_file_as_processing(self, file_entity):
        """标记文件为处理状态 - 所有块已上传完成，等待最终处理"""
        update_dict = {
            'proc_status': UploadProcStatusEnum.PROCESSING,  # 文件状态从 UPLOADING 变为 PROCESSING
            'updated_at': get_current_timestamp()
        }
        await self.file_repo.update(file_entity.uid, update_dict)

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
            
            # ✅ 创建字典而不是DTO
            update_data = {
                'total_files': file_stats["total_files"],
                'completed_files': file_stats["completed_files"],
                'failed_files': file_stats["failed_files"],
                'processing_files': file_stats["processing_files"],
                'total_size': file_stats["total_size"],
                'uploaded_size': file_stats["uploaded_size"],
                'updated_at': get_current_timestamp()  # 添加更新时间
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
                update_data['proc_status'] = UploadProcStatusEnum.UPLOADING  # 或者PROCESSING，根据你的业务逻辑
            
            # ✅ 传递字典给Repository，而不是DTO
            await self.task_repo.update(task_entity.uid, update_data)
            
            logger.info(f"Updated task progress: {task_entity.uid}, progress: {progress_percentage:.2f}%")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            return False

    async def _create_initial_files(self, task_entity: UploadTask, files: List[InitializeUploadFileInputDTO], tenant_id: str):
        """创建初始文件记录 - 修复bucket_name和存储路径设置"""
        file_entities = []
        
        for file_input in files:
            # 生成存储路径和对象名称
            storage_path = self._generate_storage_path(task_entity, file_input.original_path, file_input.filename)
            object_name = self._generate_object_name(task_entity, storage_path)
            
            # 使用 Mapper 创建文件实体
            file_entity = upload_mapper.initialize_file_input_to_upload_task_file_entity(
                file_input, task_entity.uid, tenant_id, storage_path=storage_path
            )
            
            # 设置存储信息 - 修复bucket_name设置
            file_entity.minio_bucket = settings.MINIO_BUCKET_NAME
            file_entity.minio_object_name = object_name
            file_entity.storage_path = storage_path
            file_entity.proc_status = UploadProcStatusEnum.PENDING
            
            file_entities.append(file_entity)

        # 批量创建文件
        if file_entities:
            await self.file_repo.bulk_create(file_entities)

    
    async def get_upload_task(self, task_id: str) -> GetUploadTaskResponseDTO:
        """获取上传任务详情"""
        try:
            task_entity = await self.task_repo.get_by_id(task_id)
            if not task_entity:
                return GetUploadTaskResponseDTO(
                    success=False,
                    errors=[ErrorDTO(message="Task not found", code="TASK_NOT_FOUND")]
                )

            task_dto = await self._get_task_dto_with_files(task_entity)
            
            return GetUploadTaskResponseDTO(
                success=True,
                data=task_dto
            )
        except Exception as e:
            logger.error(f"Get upload task failed: {str(e)}")
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
            logger.error(f"List upload tasks failed: {str(e)}")
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
            logger.error(f"List upload task files failed: {str(e)}")
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
            logger.error(f"Get upload progress failed: {str(e)}")
            return None

    def _validate_initialize_input(self, input_dto: InitializeUploadInputDTO) -> List[ErrorDTO]:
        """验证初始化输入"""
        errors = []
        
        if not input_dto.title or len(input_dto.title.strip()) == 0:
            errors.append(ErrorDTO(message="Title is required", code="MISSING_TITLE"))
            
        if not input_dto.source_paths:
            errors.append(ErrorDTO(message="Source paths are required", code="MISSING_SOURCE_PATHS"))
            
        if input_dto.chunk_size <= 0:
            errors.append(ErrorDTO(message="Chunk size must be positive", code="INVALID_CHUNK_SIZE"))
            
        if input_dto.max_parallel_uploads <= 0:
            errors.append(ErrorDTO(message="Max parallel uploads must be positive", code="INVALID_PARALLEL_UPLOADS"))
            
        return errors

    async def _resume_existing_task(self, input_dto: InitializeUploadInputDTO) -> InitializeUploadResponseDTO:
        """恢复现有任务"""
        existing_task = await self.task_repo.get_by_id(input_dto.resume_task_id)
        if not existing_task:
            return InitializeUploadResponseDTO(
                success=False,
                errors=[ErrorDTO(message="Resume task not found", code="RESUME_TASK_NOT_FOUND")]
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
        print("=============_validate_chunk_sequence==============")
        existing_chunk = await self.chunk_repo.get_by_file_and_number(
            file_entity.uid, chunk_number
        )
        print(f"_validate_chunk_sequence:file_entity.uid={file_entity.uid},chunk_number={str(chunk_number)}")
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
        """验证所有块都已上传 - 添加详细日志"""
        try:
            uploaded_count = await self.chunk_repo.count_by_file(file_entity.uid)
            total_chunks = file_entity.total_chunks
            
            logger.info(f"Chunk validation: uploaded={uploaded_count}, total={total_chunks}, file={file_entity.filename}")
            
            # 获取所有分块详情
            chunks = await self.chunk_repo.list_by_file(file_entity.uid)
            for chunk in chunks:
                logger.info(f"Chunk {chunk.chunk_number}: {chunk.minio_object_name}, status: {chunk.proc_status}")
            
            return uploaded_count == total_chunks
        except Exception as e:
            logger.error(f"Chunk validation failed: {e}")
            return False

    async def _get_chunk_parts(self, file_id: str) -> List[Dict]:
        """获取块部件列表用于合并"""
        chunks = await self.chunk_repo.list_by_file(file_id)
        return [
            {
                "part_number": chunk.chunk_number,
                "etag": chunk.minio_etag,
                # 不需要 object_name，因为可以从 chunk 实体中获取
            }
            for chunk in chunks
        ]
    

    async def _validate_file_integrity(self, file_entity, input_dto: CompleteUploadInputDTO) -> bool:
        """验证文件完整性"""
        # 这里可以实现MD5/SHA256校验
        # 暂时返回True，实际实现中需要根据存储服务进行验证
        return True

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

    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """发布事件（简化实现）"""
        if self.event_bus:
            try:
                await self.event_bus.publish(event_type, data)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {str(e)}")

    async def _record_metric(self, metric_name: str, value: float = 1.0):
        """记录指标（简化实现）"""
        if self.metrics_collector:
            try:
                await self.metrics_collector.increment_counter(metric_name, value)
            except Exception as e:
                logger.warning(f"Failed to record metric {metric_name}: {str(e)}")
   
    async def _fix_missing_storage_info(self, file_entity: UploadTaskFile, task_entity: UploadTask):
        """修复缺失的存储信息"""
        # 生成存储路径和对象名称
        storage_path = self._generate_storage_path(task_entity, file_entity.original_path, file_entity.filename)
        object_name = self._generate_object_name(task_entity, storage_path)
        
        update_data = {
            'storage_path': storage_path,
            'minio_bucket': settings.MINIO_BUCKET_NAME,
            'minio_object_name': object_name,
            'updated_at': get_current_timestamp()
        }
        
        await self.file_repo.update(file_entity.uid, update_data)
        logger.info(f"Fixed missing storage info for file: {file_entity.uid}")

    @staticmethod
    def _generate_storage_path(task: UploadTask, original_path: str, filename: str) -> str:
        """生成存储路径 - 兼容 Windows 和 macOS 路径"""
        # 清理文件名，移除路径和非法字符
        safe_filename = UploadService._sanitize_filename(filename)
        
        if task.preserve_structure and task.base_upload_path:
            # 保持目录结构，但只保留相对路径部分
            relative_path = UploadService._extract_relative_path(original_path)
            if relative_path:
                # 清理路径中的每个部分
                path_parts = []
                for part in relative_path.split('/'):
                    clean_part = UploadService._sanitize_filename(part)
                    if clean_part and clean_part not in ['.', '..']:  # 防止路径遍历
                        path_parts.append(clean_part)
                
                if path_parts:
                    clean_dir_path = '/'.join(path_parts)
                    return f"{task.base_upload_path}/{clean_dir_path}/{safe_filename}"
            
            # 如果没有有效的相对路径，直接放在基础路径下
            return f"{task.base_upload_path}/{safe_filename}"
        elif task.base_upload_path:
            # 基础上传路径
            return f"{task.base_upload_path}/{safe_filename}"
        else:
            # 直接使用文件名
            return safe_filename

    @staticmethod
    def _extract_relative_path(full_path: str) -> str:
        """从完整路径中提取相对路径部分 - 兼容 Windows 和 macOS"""
        if not full_path:
            return ""
        
        # 统一使用正斜杠
        path = full_path.replace('\\', '/')
        
        # 处理 Windows 绝对路径 (C:\Users\... 或 \\server\share\...)
        if re.match(r'^[a-zA-Z]:/', path):  # Windows 盘符路径
            # 移除盘符部分 (C:/Users/... -> Users/...)
            path = '/'.join(path.split('/')[1:])
        elif path.startswith('//') or path.startswith('\\\\'):  # Windows 网络路径
            # 移除网络路径前缀 (//server/share/... -> share/...)
            path = '/'.join(path.split('/')[2:])
        
        # 处理 Unix/Mac 绝对路径
        elif path.startswith('/'):
            # 对于绝对路径，我们只保留最后几级目录，避免过深的路径
            path_parts = path.split('/')
            # 保留最后3级目录（可根据需要调整）
            if len(path_parts) > 3:
                path_parts = path_parts[-3:]
            path = '/'.join([part for part in path_parts if part])  # 移除空部分
        
        # 移除常见的系统目录前缀
        common_prefixes = [
            'Users/', 'home/', 'Documents/', 'Downloads/', 'Desktop/',
            'tmp/', 'temp/', 'var/tmp/'
        ]
        
        for prefix in common_prefixes:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        
        return path

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名，移除非法字符和路径信息"""
        if not filename:
            return "unnamed_file"
        
        # 提取纯文件名（移除路径）
        clean_name = os.path.basename(filename)
        
        # MinIO/S3 不允许的字符：\ { } ^ % ` [ ] " > < ~ # | 
        # 替换这些字符为下划线
        illegal_chars = r'[\\{}^%`\[\]"<>~#|]'
        clean_name = re.sub(illegal_chars, '_', clean_name)
        
        # 可选：替换空格为下划线（根据需求决定）
        # clean_name = clean_name.replace(' ', '_')
        
        # 移除连续的下划线
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # 移除开头和结尾的特殊字符
        clean_name = clean_name.strip('_.-')
        
        # 如果名称为空，使用默认名称
        if not clean_name:
            clean_name = "unnamed_file"
        
        # 限制文件名长度（避免过长的对象名称）
        if len(clean_name) > 255:
            name, ext = os.path.splitext(clean_name)
            clean_name = name[:255-len(ext)] + ext
        
        return clean_name

    @staticmethod
    def _generate_object_name(task: UploadTask, storage_path: str) -> str:
        """生成MinIO对象名称 - 确保路径有效性"""
        # 清理存储路径
        clean_storage_path = storage_path
        
        # 移除开头的斜杠和重复的斜杠
        clean_storage_path = re.sub(r'^/+', '', clean_storage_path)
        clean_storage_path = re.sub(r'/+', '/', clean_storage_path)
        
        # 生成对象名称
        object_name = f"uploads/{task.uid}/{clean_storage_path}"
        
        # 最终清理：确保没有重复斜杠
        object_name = re.sub(r'/+', '/', object_name)
        
        # 记录生成的路径用于调试
        logger.debug(f"Generated object name: {object_name}")
        
        return object_name     