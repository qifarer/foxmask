# foxmask/file/services/upload_service.py
import os
import asyncio
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from foxmask.file.dtos.upload import (
    UploadTaskInitDTO,
    UploadTaskFileDTO,
    UploadTaskFileChunkDTO,
    UploadTaskCompleteDTO,
    UploadTaskQueryDTO
)
from foxmask.file.models.upload import (
    UploadTask, 
    UploadTaskFile, 
    UploadTaskFileChunk,
)
from foxmask.file.enums import (
    UploadProcStatusEnum,
    UploadSourceTypeEnum, 
    UploadStrategyEnum,
    UploadTaskTypeEnum
)

from foxmask.file.repositories import get_repository_manager
from foxmask.utils.helpers import generate_uuid, get_current_timestamp
from foxmask.core.config import settings
from foxmask.core.logger import logger

class BusinessException(Exception):
    """业务异常"""
    pass


class PermissionDeniedException(Exception):
    """权限拒绝异常"""
    pass


class UploadService:
    """上传服务"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
        self.task_repo = self.repo_manager.upload_task_repository
        self.task_file_repo = self.repo_manager.upload_task_file_repository
        self.task_chunk_repo = self.repo_manager.upload_task_file_chunk_repository
        self.minio_repo = self.repo_manager.minio_repository
    
    def _dto_to_task_entity(self, init_dto: UploadTaskInitDTO) -> UploadTask:
        """DTO转换为任务实体"""
        return UploadTask(
            uid=generate_uuid(),
            tenant_id=init_dto.tenant_id,
            title=init_dto.title,
            desc=init_dto.desc,
            source_type=init_dto.source_type,
            source_paths=[file_info.original_path for file_info in init_dto.files],
            upload_strategy=init_dto.upload_strategy,
            max_parallel_uploads=init_dto.max_parallel_uploads,
            chunk_size=init_dto.chunk_size,
            preserve_structure=init_dto.preserve_structure,
            base_upload_path=init_dto.base_upload_path,
            auto_extract_metadata=init_dto.auto_extract_metadata,
            file_type_filters=init_dto.file_type_filters,
            max_file_size=init_dto.max_file_size,
            created_by=init_dto.created_by,
            task_status=UploadProcStatusEnum.PENDING,
            total_files=0,
            total_size=0,
            uploaded_size=0,
            discovered_files=0,
            processing_files=0,
            completed_files=0,
            failed_files=0
        )
    
    def _dto_to_task_file_entity(self, file_dto: UploadTaskFileDTO, task: UploadTask, total_chunks: int) -> UploadTaskFile:
        """DTO转换为文件实体"""
        return UploadTaskFile(
            uid=generate_uuid(),
            tenant_id=task.tenant_id,
            master_id=task.uid,
            original_path=file_dto.original_path,
            storage_path=file_dto.storage_path,
            filename=file_dto.filename,
            file_size=file_dto.file_size,
            file_type=file_dto.file_type,
            content_type=file_dto.content_type,
            extension=file_dto.extension,
            checksum_md5=file_dto.checksum_md5,
            checksum_sha256=file_dto.checksum_sha256,
            total_chunks=total_chunks,
            uploaded_chunks=0,
            current_chunk=0,
            progress=0.0,
            extracted_metadata=file_dto.extracted_metadata,
            file_status=UploadProcStatusEnum.PENDING
        )
    
  
    
    def _dto_to_task_chunk_entity(self, chunk_dto: UploadTaskFileChunkDTO, task: UploadTask, file_record: UploadTaskFile) -> UploadTaskFileChunk:
        """DTO转换为分块实体"""
        start_byte = (chunk_dto.chunk_number - 1) * task.chunk_size
        end_byte = min(start_byte + task.chunk_size, file_record.file_size) - 1
        is_final_chunk = (end_byte >= file_record.file_size - 1)
        
        minio_object_name = f"{file_record.uid}/chunk_{chunk_dto.chunk_number:06d}"
        
        return UploadTaskFileChunk(
            uid=generate_uuid(),
            tenant_id=task.tenant_id,
            master_id=task.uid,
            file_id=file_record.uid,
            chunk_number=chunk_dto.chunk_number,
            chunk_size=chunk_dto.chunk_size,
            start_byte=start_byte,
            end_byte=end_byte,
            is_final_chunk=is_final_chunk,
            minio_bucket=settings.MINIO_BUCKET_NAME,
            minio_object_name=minio_object_name,
            chunk_status=UploadProcStatusEnum.PENDING,
            retry_count=0,
            max_retries=3
        )
    
    def _calculate_remaining_time(self, task: UploadTask) -> Optional[float]:
        """计算剩余时间"""
        if task.uploaded_size == 0 or task.total_size == 0:
            return None
        
        # 简单的线性估算
        elapsed_time = (datetime.now() - task.created_at).total_seconds()
        if elapsed_time == 0:
            return None
        
        upload_speed = task.uploaded_size / elapsed_time
        remaining_size = task.total_size - task.uploaded_size
        
        if upload_speed > 0:
            return remaining_size / upload_speed
        
        return None
    
    async def init_upload_task(self, init_dto: UploadTaskInitDTO) -> Dict[str, Any]:
        """统一初始化上传任务和文件信息"""
        try:
            # DTO转换为任务实体
            task_entity = self._dto_to_task_entity(init_dto)
            
            # 调用Repository保存任务
            print("=========task_entity======")
            task = await self.task_repo.create(task_entity)
            
            total_size = 0
            total_chunks = 0
            file_entities = []
            
            # 创建文件记录
            for file_dto in init_dto.files:
                # 计算总分块数
                file_chunks = (file_dto.file_size + task.chunk_size - 1) // task.chunk_size
                total_chunks += file_chunks
                
                # DTO转换为文件实体
                file_entity = self._dto_to_task_file_entity(file_dto, task, file_chunks)
                file_entities.append(file_entity)
                total_size += file_dto.file_size
            print("=========task_file_repo======")
            # 调用Repository批量保存文件
            if file_entities:
                saved_files = await self.task_file_repo.bulk_create(file_entities)
            else:
                saved_files = []
            
            # 预创建分块记录
            if init_dto.upload_strategy == UploadStrategyEnum.SEQUENTIAL:
                await self._pre_create_chunks(task, saved_files)
            
            print("=========update_data,total_chunks======")
            # 更新任务统计信息
            update_data = {
                "total_files": len(saved_files),
                "total_size": total_size,
                "discovered_files": len(saved_files),
                "proc_status": UploadProcStatusEnum.UPLOADING
            }
            print("=========update_data,total_chunks end======")
            await self.task_repo.update(task.id, update_data)
            
            return {
                "task": task,
                "files": saved_files,
                "total_files": len(saved_files),
                "total_size": total_size,
                "total_chunks": total_chunks
            }
            
        except Exception as e:
            raise BusinessException(f"初始化上传任务失败: {str(e)}")
    
    async def _pre_create_chunks(self, task: UploadTask, file_records: List[UploadTaskFile]):
        """预创建分块记录"""
        chunk_entities = []
        
        for file_record in file_records:
            for i in range(file_record.total_chunks):
                start_byte = i * task.chunk_size
                end_byte = min(start_byte + task.chunk_size, file_record.file_size) - 1
                is_final_chunk = (i == file_record.total_chunks - 1)
                chunk_size = end_byte - start_byte + 1
                
                minio_object_name = f"{file_record.file_id}/chunk_{i:06d}"
                
                chunk_entity = UploadTaskFileChunk(
                    uid=generate_uuid(),
                    tenant_id=task.tenant_id,
                    master_id=task.uid,
                    file_id=file_record.uid,
                    chunk_number=i + 1,
                    chunk_size=chunk_size,
                    start_byte=start_byte,
                    end_byte=end_byte,
                    is_final_chunk=is_final_chunk,
                    minio_bucket=settings.MINIO_BUCKET_NAME,
                    minio_object_name=minio_object_name,
                    chunk_status=UploadProcStatusEnum.PENDING,
                    retry_count=0,
                    max_retries=3
                )
                
                chunk_entities.append(chunk_entity)
        
        if chunk_entities:
            await self.task_chunk_repo.bulk_create(chunk_entities)
    
    async def upload_chunk(self, chunk_dto: UploadTaskFileChunkDTO) -> Dict[str, Any]:
        """上传文件分块"""
        try:
            print("===================upload_chunk. start ============")
            # 调用Repository获取任务和文件
            task = await self.task_repo.get_by_id(chunk_dto.task_id)
            if not task:
                raise BusinessException("上传任务不存在")
            print("===================upload_chunk. get_by_file_id ============")
            file_record = await self.task_file_repo.get_by_file_id(chunk_dto.file_id)
            if not file_record:
                raise BusinessException("文件记录不存在")
            
            # 权限检查
            #if not await self._check_task_permission(task, user):
            #    raise BusinessException("无权访问此上传任务")
            
            # 验证分块数据
            if len(chunk_dto.chunk_data) != chunk_dto.chunk_size:
                raise BusinessException(f"分块大小不匹配: 期望{chunk_dto.chunk_size}, 实际{len(chunk_dto.chunk_data)}")
            print("==============task_chunk_repo.create============")
            # 获取或创建分块记录
            chunk = await self.task_chunk_repo.get_chunk(chunk_dto.file_id, chunk_dto.chunk_number)
            if not chunk:
                chunk_entity = self._dto_to_task_chunk_entity(chunk_dto, task, file_record)
                chunk = await self.task_chunk_repo.create(chunk_entity)
            print("==============minio_repo.upload_chunk============")
            
            # 使用MinIO Repository上传文件
            minio_etag = await self.minio_repo.upload_chunk(
                bucket_name=chunk.minio_bucket,
                object_name=chunk.minio_object_name,
                chunk_data=chunk_dto.chunk_data,
                content_type="application/octet-stream"
            )
            
            # 计算校验和
            checksum_md5 = hashlib.md5(chunk_dto.chunk_data).hexdigest()
            checksum_sha256 = hashlib.sha256(chunk_dto.chunk_data).hexdigest()
            
            print("==============task_chunk_repo.update============")
            # 更新分块状态
            chunk_update = {
                "chunk_status": UploadProcStatusEnum.COMPLETED,
                "minio_etag": minio_etag,
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256,
                "uploaded_at": datetime.now()
            }
            await self.task_chunk_repo.update(chunk.id, chunk_update)
            
            # 更新文件进度
            new_uploaded_chunks = file_record.uploaded_chunks + 1
            progress = (new_uploaded_chunks / file_record.total_chunks) * 100
            
            file_update = {
                "uploaded_chunks": new_uploaded_chunks,
                "current_chunk": chunk_dto.chunk_number,
                "progress": progress
            }
            
            if new_uploaded_chunks == 1:
                file_update["upload_started_at"] = datetime.now()
                file_update["file_status"] = UploadProcStatusEnum.UPLOADING
            
            await self.task_file_repo.update(file_record.id, file_update)
            
            # 更新任务进度
            task_update = {
                "uploaded_size": task.uploaded_size + len(chunk_dto.chunk_data)
            }
            await self.task_repo.update(task.id, task_update)
            
            # 如果是最后分块，标记文件上传完成
            if chunk_dto.is_final_chunk:
                await self._mark_file_completed(file_record)
            
            return {
                "file_id": chunk_dto.file_id,
                "next_chunk": chunk_dto.chunk_number + 1,
                "progress": progress,
                "is_completed": chunk_dto.is_final_chunk
            }
            
        except Exception as e:
            if 'chunk' in locals():
                await self._handle_chunk_upload_failure(chunk, str(e))
            raise BusinessException(f"分块上传失败: {str(e)}")
    
    async def _mark_file_completed(self, file_record: UploadTaskFile):
        """标记文件上传完成"""
        file_update = {
            "file_status": UploadProcStatusEnum.COMPLETED,
            "progress": 100.0,
            "upload_completed_at": datetime.now()
        }
        await self.task_file_repo.update(file_record.id, file_update)
    
    async def _handle_chunk_upload_failure(self, chunk: UploadTaskFileChunk, error: str):
        """处理分块上传失败"""
        if chunk.retry_count < chunk.max_retries:
            # 重试
            chunk_update = {
                "retry_count": chunk.retry_count + 1,
                "chunk_status": UploadProcStatusEnum.RETRYING
            }
            await self.task_chunk_repo.update(chunk.id, chunk_update)
        else:
            # 标记为失败
            chunk_update = {
                "chunk_status": UploadProcStatusEnum.FAILED,
                "error_info": {"error": error, "retry_count": chunk.retry_count}
            }
            await self.task_chunk_repo.update(chunk.id, chunk_update)
            
            # 更新文件状态为失败
            file_record = await self.task_file_repo.get_by_file_id(chunk.file_id)
            if file_record:
                file_update = {
                    "file_status": UploadProcStatusEnum.FAILED,
                    "error_info": {"chunk_failure": error}
                }
                await self.task_file_repo.update(file_record.id, file_update)
    
    async def complete_upload_task(self, complete_dto: UploadTaskCompleteDTO, user: Dict[str, Any]) -> Dict[str, Any]:
        """完成上传任务"""
        try:
            # 调用Repository获取任务
            task = await self.task_repo.get_by_id(complete_dto.task_id)
            if not task:
                raise BusinessException("上传任务不存在")
            
            if not await self._check_task_permission(task, user):
                raise BusinessException("无权访问此上传任务")
            
            if task.task_status in [UploadProcStatusEnum.COMPLETED, UploadProcStatusEnum.CANCELLED]:
                raise BusinessException(f"任务已{task.task_status}，无法完成")
            
            # 调用Repository获取所有文件
            files = await self.task_file_repo.get_by_task_id(complete_dto.task_id)
            
            completed_files = 0
            failed_files = 0
            
            for file_record in files:
                if file_record.file_status == UploadProcStatusEnum.COMPLETED:
                    completed_files += 1
                elif file_record.file_status == UploadProcStatusEnum.FAILED:
                    failed_files += 1
            
            # 验证是否可以完成
            if not complete_dto.force_complete and failed_files > 0:
                raise BusinessException(f"存在{failed_files}个失败文件，请重试或强制完成")
            
            # 更新任务状态
            if failed_files == 0 or complete_dto.force_complete:
                new_status = UploadProcStatusEnum.COMPLETED
            else:
                new_status = UploadProcStatusEnum.PARTIALLY_COMPLETED
            
            task_update = {
                "task_status": new_status,
                "completed_files": completed_files,
                "failed_files": failed_files
            }
            await self.task_repo.update(task.id, task_update)
            
            # 调用文件管理模块创建文件记录
            await self._create_files_in_management(task, files)
            
            return {
                "completed_files": completed_files,
                "failed_files": failed_files,
                "total_files": len(files),
                "task_status": new_status
            }
            
        except Exception as e:
            raise BusinessException(f"完成上传任务失败: {str(e)}")
    
    async def _create_files_in_management(self, task: UploadTask, files: List[UploadTaskFile]):
        """在文件管理模块中创建文件记录"""
        # 这里需要导入文件管理服务
        # from foxmask.file.services.management import FileManagementService
        # file_management = FileManagementService()
        
        for file_record in files:
            if file_record.file_status == UploadProcStatusEnum.COMPLETED:
                file_data = {
                    "file_id": file_record.uid,
                    "filename": file_record.filename,
                    "file_size": file_record.file_size,
                    "file_type": file_record.file_type,
                    "content_type": file_record.content_type,
                    "storage_path": file_record.storage_path,
                    "checksum_md5": file_record.checksum_md5,
                    "checksum_sha256": file_record.checksum_sha256,
                    "metadata": file_record.extracted_metadata,
                    "created_by": task.created_by,
                    "tenant_id": task.tenant_id
                }
                
                try:
                    # await file_management.create_file(file_data)
                    print(f"创建文件记录: {file_record.filename}")
                except Exception as e:
                    print(f"文件管理创建失败 {file_record.filename}: {e}")
    
    async def _check_task_permission(self, task: UploadTask, user: Dict[str, Any]) -> bool:
        """检查任务访问权限"""
        return task.tenant_id == user.get("tenant_id") and task.created_by == user.get("user_id")
    
    # 查询方法
    async def get_task(self, task_id: str, user: Dict[str, Any]) -> Optional[UploadTask]:
        """获取上传任务"""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        
        if not await self._check_task_permission(task, user):
            raise PermissionDeniedException("无权访问此上传任务")
        
        return task
    
    async def list_tasks(
        self,
        user: Dict[str, Any],
        task_type: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[UploadTask]:
        """获取上传任务列表"""
        tenant_id = user.get("tenant_id")
        
        # 构建查询参数
        query_params = {}
        if task_type:
            query_params["task_type"] = task_type
        if source_type:
            query_params["source_type"] = source_type
        if status:
            query_params["task_status"] = status
        if created_by:
            query_params["created_by"] = created_by
        
        return await self.task_repo.get_by_filters(
            tenant_id=tenant_id,
            filters=query_params,
            page=page,
            page_size=page_size
        )
    
    async def get_task_files(
        self,
        task_id: str,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None
    ) -> List[UploadTaskFile]:
        """获取任务文件列表"""
        if user:
            task = await self.get_task(task_id, user)
            if not task:
                return []
        
        filters = {}
        if status:
            filters["file_status"] = status
            
        return await self.task_file_repo.get_by_task_id(
            task_id=task_id,
            filters=filters,
            page=page,
            page_size=page_size
        )
    
    async def get_file_chunks(self, file_id: str) -> List[UploadTaskFileChunk]:
        """获取文件分块列表"""
        return await self.task_chunk_repo.get_by_file_id(file_id)
    
   
    
    async def get_upload_stats(self, user: Dict[str, Any]) -> UploadProcStatusEnum:
        """获取上传统计信息"""
        tenant_id = user.get("tenant_id")
        
        # 获取任务统计
        total_tasks = await self.task_repo.count({"tenant_id": tenant_id})
        active_tasks = await self.task_repo.count({
            "tenant_id": tenant_id,
            "task_status": {"$in": ["PENDING", "UPLOADING", "PROCESSING"]}
        })
        completed_tasks = await self.task_repo.count({
            "tenant_id": tenant_id,
            "task_status": "COMPLETED"
        })
        failed_tasks = await self.task_repo.count({
            "tenant_id": tenant_id,
            "task_status": "FAILED"
        })
        
        # 获取文件统计
        total_files_uploaded = await self.task_file_repo.count({
            "tenant_id": tenant_id,
            "file_status": "COMPLETED"
        })
        
        # 计算总数据量
        pipeline = [
            {"$match": {"tenant_id": tenant_id, "file_status": "COMPLETED"}},
            {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
        ]
        result = await self.task_file_repo.aggregate(pipeline)
        total_data_uploaded = result[0]["total_size"] if result else 0
        
        return UploadStatsType(
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            total_files_uploaded=total_files_uploaded,
            total_data_uploaded=total_data_uploaded,
            average_upload_speed=None
        )
    
    async def cancel_upload_task(self, task_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """取消上传任务"""
        try:
            task = await self.get_task(task_id, user)
            if not task:
                raise BusinessException("上传任务不存在")
            
            if task.task_status in [UploadProcStatusEnum.COMPLETED, UploadProcStatusEnum.CANCELLED]:
                raise BusinessException(f"任务已{task.task_status}，无法取消")
            
            # 更新任务状态
            await self.task_repo.update_task_status(task_id, UploadProcStatusEnum.CANCELLED)
            
            # 清理MinIO中的临时文件
            await self._cleanup_minio_files(task_id)
            
            return {
                "success": True,
                "message": "上传任务已取消"
            }
            
        except Exception as e:
            raise BusinessException(f"取消上传任务失败: {str(e)}")

    async def retry_failed_files(self, task_id: str, file_ids: Optional[List[str]], user: Dict[str, Any]):
        """重试失败的文件"""
        task = await self.get_task(task_id, user)
        if not task:
            raise BusinessException("上传任务不存在")
        
        # 构建查询条件
        query = {"master_id": task_id, "file_status": UploadProcStatusEnum.FAILED}
        if file_ids:
            query["file_id"] = {"$in": file_ids}
        
        failed_files = await self.task_file_repo.get_by_filters(query)
        
        for file in failed_files:
            # 重置文件状态
            await self.task_file_repo.update_file_status(
                file.file_id, 
                UploadProcStatusEnum.PENDING,
                uploaded_chunks=0,
                current_chunk=0,
                progress=0.0,
                upload_started_at=None,
                upload_completed_at=None,
                error_info=None
            )
            
            # 重置分块状态
            chunks = await self.task_chunk_repo.get_by_file_id(file.file_id)
            for chunk in chunks:
                await self.task_chunk_repo.update(
                    chunk.id,
                    {
                        "chunk_status": UploadProcStatusEnum.PENDING,
                        "retry_count": 0,
                        "uploaded_at": None,
                        "error_info": None
                    }
                )
        
        # 更新任务状态
        if task.task_status == UploadProcStatusEnum.FAILED:
            await self.task_repo.update_task_status(task_id, UploadProcStatusEnum.UPLOADING)

    async def _cleanup_minio_files(self, task_id: str):
        """清理MinIO中的临时文件"""
        try:
            files = await self.task_file_repo.get_by_task_id(task_id)
            for file in files:
                chunks = await self.task_chunk_repo.get_by_file_id(file.uid)
                for chunk in chunks:
                    await self.minio_repo.delete_chunk(
                        chunk.minio_bucket,
                        chunk.minio_object_name
                    )
        except Exception as e:
            logger.error(f"Failed to cleanup MinIO files for task {task_id}: {e}")