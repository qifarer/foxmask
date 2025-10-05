# -*- coding: utf-8 -*-
# foxmask/file/mappers/upload_mapper.py
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

from foxmask.file.models.upload import UploadTask, UploadTaskFile, UploadTaskFileChunk
from foxmask.file.dtos.upload import *
from foxmask.utils.helpers import get_current_timestamp, generate_uuid
from foxmask.core.enums import Status, Visibility
from foxmask.file.enums import UploadProcStatusEnum, UploadSourceTypeEnum, UploadStrategyEnum, FileTypeEnum

class UploadMapper:
    """上传模块统一的 Mapper 层"""
    
    # ==================== Entity to DTO 转换 ====================
    
    @staticmethod
    def entity_to_upload_task_dto(entity: UploadTask, include_files: bool = False) -> UploadTaskDTO:
        """UploadTask Entity 转 DTO"""
        if not entity:
            return None
            
        files_dto = None
        if include_files and hasattr(entity, 'files') and entity.files:
            files_dto = [UploadMapper.entity_to_upload_task_file_dto(file_entity) for file_entity in entity.files]
        
        return UploadTaskDTO(
            # Base fields
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            title=entity.title,
            desc=entity.desc,
            category=entity.category,
            tags=entity.tags or [],
            note=entity.note,
            status=entity.status,
            visibility=entity.visibility,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
            created_by=entity.created_by,
            allowed_users=entity.allowed_users or [],
            allowed_roles=entity.allowed_roles or [],
            proc_meta=entity.proc_meta,
            error_info=entity.error_info,
            metadata=entity.metadata,
            
            # Upload specific fields
            proc_status=entity.proc_status,
            source_type=entity.source_type,
            source_paths=entity.source_paths or [],
            upload_strategy=entity.upload_strategy,
            max_parallel_uploads=entity.max_parallel_uploads,
            chunk_size=entity.chunk_size,
            preserve_structure=entity.preserve_structure,
            base_upload_path=entity.base_upload_path,
            auto_extract_metadata=entity.auto_extract_metadata,
            file_type_filters=entity.file_type_filters or [],
            max_file_size=entity.max_file_size,
            
            # Progress fields
            discovered_files=entity.discovered_files,
            processing_files=entity.processing_files,
            total_files=entity.total_files,
            completed_files=entity.completed_files,
            failed_files=entity.failed_files,
            total_size=entity.total_size,
            uploaded_size=entity.uploaded_size,
            
            # Timestamps
            discovery_started_at=entity.discovery_started_at,
            discovery_completed_at=entity.discovery_completed_at,
            
            # Nested objects
            files=files_dto
        )
    
    @staticmethod
    def entity_to_upload_task_file_dto(entity: UploadTaskFile, include_chunks: bool = False) -> UploadTaskFileDTO:
        """UploadTaskFile Entity 转 DTO"""
        if not entity:
            return None
            
        chunks_dto = None
        if include_chunks and hasattr(entity, 'chunks') and entity.chunks:
            chunks_dto = [UploadMapper.entity_to_upload_task_file_chunk_dto(chunk_entity) for chunk_entity in entity.chunks]
        
        return UploadTaskFileDTO(
            # Base fields
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            master_id=entity.master_id,
            note=entity.note,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            
            # File specific fields
            proc_status=entity.proc_status,
            original_path=entity.original_path,
            storage_path=entity.storage_path,
            filename=entity.filename,
            file_size=entity.file_size,
            file_type=entity.file_type,
            content_type=entity.content_type,
            extension=entity.extension,
            
            # 存储信息
            minio_bucket=entity.minio_bucket,
            minio_object_name=entity.minio_object_name,
            minio_etag=entity.minio_etag,
            checksum_md5=entity.checksum_md5,
            checksum_sha256=entity.checksum_sha256,
            
            # 上传控制
            total_chunks=entity.total_chunks,
            uploaded_chunks=entity.uploaded_chunks,
            current_chunk=entity.current_chunk,
            
            # 进度信息
            progress=entity.progress,
            upload_speed=entity.upload_speed,
            estimated_time_remaining=entity.estimated_time_remaining,
            
            # 元数据
            extracted_metadata=entity.extracted_metadata or {},
            
            # 时间戳
            upload_started_at=entity.upload_started_at,
            upload_completed_at=entity.upload_completed_at,
            
            # Nested objects
            chunks=chunks_dto
        )
    
    @staticmethod
    def entity_to_upload_task_file_chunk_dto(entity: UploadTaskFileChunk) -> UploadTaskFileChunkDTO:
        """UploadTaskFileChunk Entity 转 DTO"""
        if not entity:
            return None
            
        return UploadTaskFileChunkDTO(
            # Base fields
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            master_id=entity.master_id,
            note=entity.note,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            
            # Chunk specific fields
            proc_status=entity.proc_status,
            file_id=entity.file_id,
            chunk_number=entity.chunk_number,
            chunk_size=entity.chunk_size,
            start_byte=entity.start_byte,
            end_byte=entity.end_byte,
            is_final_chunk=entity.is_final_chunk,
            minio_bucket=entity.minio_bucket,
            minio_object_name=entity.minio_object_name,
            minio_etag=entity.minio_etag,
            checksum_md5=entity.checksum_md5,
            checksum_sha256=entity.checksum_sha256,
            retry_count=entity.retry_count,
            max_retries=entity.max_retries
        )
    
    # ==================== DTO to Entity 转换 ====================
    
    @staticmethod
    def initialize_input_to_upload_task_entity(dto: InitializeUploadInputDTO) -> UploadTask:
        """InitializeUploadInputDTO 转 UploadTask Entity"""
        if not dto:
            return None
            
        now = get_current_timestamp()
        uid = generate_uuid()
        
        return UploadTask(
            # Base fields
            uid=uid,
            tenant_id=dto.tenant_id,
            created_by=dto.created_by,
            title=dto.title,
            desc=dto.desc,
            status=Status.DRAFT,  # ✅ 使用枚举
            visibility=Visibility.PUBLIC,  # ✅ 使用枚举
            created_at=now,
            updated_at=now,
            
            # Upload specific fields
            proc_status=UploadProcStatusEnum.PENDING,
            source_type=dto.source_type,
            source_paths=dto.source_paths,
            upload_strategy=dto.upload_strategy,
            max_parallel_uploads=dto.max_parallel_uploads,
            chunk_size=dto.chunk_size,
            preserve_structure=dto.preserve_structure,
            base_upload_path=dto.base_upload_path,
            auto_extract_metadata=dto.auto_extract_metadata,
            file_type_filters=dto.file_type_filters or [],
            max_file_size=dto.max_file_size,
            
            # Progress fields (初始化为0)
            discovered_files=0,
            processing_files=0,
            total_files=0,
            completed_files=0,
            failed_files=0,
            total_size=0,
            uploaded_size=0
        )
    
    @staticmethod
    def initialize_file_input_to_upload_task_file_entity(
        dto: InitializeUploadFileInputDTO, 
        task_id: str, 
        tenant_id: str,
        storage_path: str = ""  # ✅ 添加存储路径参数
    ) -> UploadTaskFile:
        """InitializeUploadFileInputDTO 转 UploadTaskFile Entity"""
        if not dto:
            return None
            
        now = get_current_timestamp()
        uid = generate_uuid()
        total_chunks = (dto.file_size + dto.chunk_size - 1) // dto.chunk_size
        
        return UploadTaskFile(
            # Base fields
            uid=uid,
            tenant_id=tenant_id,
            master_id=task_id,
            created_at=now,
            updated_at=now,
            
            # File specific fields
            proc_status=UploadProcStatusEnum.PENDING,
            original_path=dto.original_path,
            storage_path=storage_path,  # ✅ 使用传入的存储路径
            filename=dto.filename,
            file_size=dto.file_size,
            file_type=dto.file_type,
            content_type=dto.content_type,
            extension=dto.extension,
            
            # 上传控制
            total_chunks=total_chunks,
            uploaded_chunks=0,
            current_chunk=0,
            
            # 进度信息
            progress=0.0,
            
            # 元数据
            extracted_metadata={}
        )
    
    @staticmethod
    def upload_chunk_input_to_upload_task_file_chunk_entity(
        dto: UploadChunkInputDTO,
        tenant_id: str,
    ) -> UploadTaskFileChunk:
        """UploadChunkInputDTO 转 UploadTaskFileChunk Entity"""
        if not dto:
            return None
            
        now = get_current_timestamp()
        uid = generate_uuid()
        
        return UploadTaskFileChunk(
            # Base fields
            uid=uid,
            tenant_id=tenant_id,
            master_id=dto.task_id,
            created_at=now,
            updated_at=now,
            
            # Chunk specific fields
            proc_status=UploadProcStatusEnum.PENDING,
            file_id=dto.file_id,
            chunk_number=dto.chunk_number,
            chunk_size=dto.chunk_size,
            start_byte=dto.start_byte,
            end_byte=dto.end_byte,
            is_final_chunk=dto.is_final_chunk,
            minio_bucket=dto.minio_bucket,
            minio_object_name=dto.minio_object_name,
            checksum_md5=dto.checksum_md5,
            checksum_sha256=dto.checksum_sha256,
            retry_count=0,
            max_retries=dto.max_retries
        )
    
    # ==================== 批量转换方法 ====================
    
    @staticmethod
    def entities_to_upload_task_dtos(entities: List[UploadTask], include_files: bool = False) -> List[UploadTaskDTO]:
        """UploadTask Entity 列表转 DTO 列表"""
        return [UploadMapper.entity_to_upload_task_dto(entity, include_files) for entity in entities if entity]
    
    @staticmethod
    def entities_to_upload_task_file_dtos(entities: List[UploadTaskFile], include_chunks: bool = False) -> List[UploadTaskFileDTO]:
        """UploadTaskFile Entity 列表转 DTO 列表"""
        return [UploadMapper.entity_to_upload_task_file_dto(entity, include_chunks) for entity in entities if entity]
    
    @staticmethod
    def entities_to_upload_task_file_chunk_dtos(entities: List[UploadTaskFileChunk]) -> List[UploadTaskFileChunkDTO]:
        """UploadTaskFileChunk Entity 列表转 DTO 列表"""
        return [UploadMapper.entity_to_upload_task_file_chunk_dto(entity) for entity in entities if entity]
    
    # ==================== 更新转换方法 ====================
    
    @staticmethod
    def update_dto_to_upload_task_entity_update_dict(dto: UploadTaskUpdateDTO) -> Dict[str, Any]:
        """UploadTaskUpdateDTO 转 Entity 更新字典"""
        if not dto:
            return {}
            
        update_dict = {}
        fields = [
            'title', 'desc', 'category', 'tags', 'note', 'status', 
            'visibility', 'proc_status', 'proc_meta', 'error_info', 'metadata'
        ]
        
        for field in fields:
            value = getattr(dto, field, None)
            if value is not None:
                update_dict[field] = value
        
        # 更新时间戳
        update_dict['updated_at'] = get_current_timestamp()  # ✅ 使用统一的时间函数
        
        return update_dict
    
    @staticmethod
    def progress_update_dto_to_upload_task_entity_update_dict(dto: UploadTaskProgressUpdateDTO) -> Dict[str, Any]:
        """UploadTaskProgressUpdateDTO 转 Entity 更新字典"""
        if not dto:
            return {}
            
        update_dict = {}
        fields = [
            'discovered_files', 'processing_files', 'completed_files', 
            'failed_files', 'uploaded_size', 'total_files', 'total_size',
            'discovery_started_at', 'discovery_completed_at'
        ]
        
        for field in fields:
            value = getattr(dto, field, None)
            if value is not None:
                update_dict[field] = value
        
        # 更新时间戳
        update_dict['updated_at'] = get_current_timestamp()  # ✅ 使用统一的时间函数
        
        return update_dict
    
    @staticmethod
    def file_update_dto_to_upload_task_file_entity_update_dict(dto: UploadTaskFileUpdateDTO) -> Dict[str, Any]:
        """UploadTaskFileUpdateDTO 转 Entity 更新字典"""
        if not dto:
            return {}
            
        update_dict = {}
        fields = [
            'proc_status', 'uploaded_chunks', 'current_chunk', 'progress',
            'upload_speed', 'estimated_time_remaining', 'minio_etag',  # ✅ 添加minio_etag
            'checksum_md5', 'checksum_sha256', 'extracted_metadata', 
            'upload_started_at', 'upload_completed_at', 'note'
        ]
        
        for field in fields:
            value = getattr(dto, field, None)
            if value is not None:
                update_dict[field] = value
        
        # 更新时间戳
        update_dict['updated_at'] = get_current_timestamp()  # ✅ 使用统一的时间函数
        
        return update_dict
    
    # ==================== 查询条件转换 ====================
    
    @staticmethod
    def upload_task_query_dto_to_filter_dict(dto: UploadTaskQueryDTO) -> Dict[str, Any]:
        """UploadTaskQueryDTO 转 MongoDB 查询过滤器"""
        if not dto:
            return {}
            
        filter_dict = {'tenant_id': dto.tenant_id}
        
        if dto.task_id:
            filter_dict['uid'] = dto.task_id
        if dto.created_by:
            filter_dict['created_by'] = dto.created_by
        if dto.status:
            filter_dict['status'] = dto.status
        if dto.proc_status:
            filter_dict['proc_status'] = dto.proc_status
        if dto.source_type:
            filter_dict['source_type'] = dto.source_type
        if dto.category:
            filter_dict['category'] = dto.category
            
        # 时间范围查询
        time_filter = {}
        if dto.created_at_start:
            time_filter['$gte'] = dto.created_at_start
        if dto.created_at_end:
            time_filter['$lte'] = dto.created_at_end
        if time_filter:
            filter_dict['created_at'] = time_filter
            
        # 标签查询
        if dto.tags:
            filter_dict['tags'] = {'$in': dto.tags}
            
        return filter_dict
    
    @staticmethod
    def upload_task_file_query_dto_to_filter_dict(dto: UploadTaskFileQueryDTO) -> Dict[str, Any]:
        """UploadTaskFileQueryDTO 转 MongoDB 查询过滤器"""
        if not dto:
            return {}
            
        filter_dict = {'tenant_id': dto.tenant_id}
        
        if dto.task_id:
            filter_dict['master_id'] = dto.task_id
        if dto.file_id:
            filter_dict['uid'] = dto.file_id
        if dto.proc_status:
            filter_dict['proc_status'] = dto.proc_status
        if dto.file_type:
            filter_dict['file_type'] = dto.file_type
            
        return filter_dict
    
    @staticmethod
    def upload_task_file_chunk_query_dto_to_filter_dict(dto: UploadTaskFileChunkQueryDTO) -> Dict[str, Any]:
        """UploadTaskFileChunkQueryDTO 转 MongoDB 查询过滤器"""
        if not dto:
            return {}
            
        filter_dict = {'tenant_id': dto.tenant_id}
        
        if dto.file_id:
            filter_dict['file_id'] = dto.file_id
        if dto.chunk_number:
            filter_dict['chunk_number'] = dto.chunk_number
        if dto.proc_status:
            filter_dict['proc_status'] = dto.proc_status
            
        return filter_dict
    
    # ==================== 进度信息转换 ====================
    
    @staticmethod
    def entity_to_upload_progress_dto(task_entity: UploadTask, file_entities: List[UploadTaskFile] = None) -> UploadProgressDTO:
        """Entity 转 UploadProgressDTO"""
        if not task_entity:
            return None
            
        # 计算进度百分比
        total_files = max(task_entity.total_files, 1)  # 避免除零
        progress_percentage = (task_entity.completed_files / total_files) * 100 if total_files > 0 else 0
        
        current_uploading_files = None
        if file_entities:
            current_uploading_files = [
                file_entity.filename for file_entity in file_entities 
                if file_entity.proc_status in [UploadProcStatusEnum.UPLOADING, UploadProcStatusEnum.PROCESSING, UploadProcStatusEnum.PENDING]
            ]
        
        return UploadProgressDTO(
            task_id=task_entity.uid,
            total_files=task_entity.total_files,
            completed_files=task_entity.completed_files,
            failed_files=task_entity.failed_files,
            processing_files=task_entity.processing_files,  # ✅ 添加processing_files字段
            progress_percentage=progress_percentage,
            uploaded_size=task_entity.uploaded_size,
            total_size=task_entity.total_size,
            current_uploading_files=current_uploading_files
        )
    
    @staticmethod
    def entity_to_file_upload_progress_dto(file_entity: UploadTaskFile) -> FileUploadProgressDTO:
        """UploadTaskFile Entity 转 FileUploadProgressDTO"""
        if not file_entity:
            return None
            
        return FileUploadProgressDTO(
            file_id=file_entity.uid,
            filename=file_entity.filename,
            progress=file_entity.progress,
            uploaded_chunks=file_entity.uploaded_chunks,
            total_chunks=file_entity.total_chunks,
            upload_speed=file_entity.upload_speed,
            estimated_time_remaining=file_entity.estimated_time_remaining,
            current_chunk=file_entity.current_chunk
        )
    
    @staticmethod
    def entity_to_upload_resume_info_dto(file_entity: UploadTaskFile) -> UploadResumeInfoDTO:
        """UploadTaskFile Entity 转 UploadResumeInfoDTO"""
        if not file_entity:
            return None
            
        uploaded_size = int(file_entity.file_size * (file_entity.uploaded_chunks / max(file_entity.total_chunks, 1)))
        
        return UploadResumeInfoDTO(
            task_id=file_entity.master_id,
            file_id=file_entity.uid,
            uploaded_chunks=file_entity.uploaded_chunks,
            total_chunks=file_entity.total_chunks,
            next_chunk_number=file_entity.uploaded_chunks + 1,
            file_size=file_entity.file_size,
            uploaded_size=uploaded_size,
            progress=file_entity.progress
        )


# 创建 Mapper 实例
upload_mapper = UploadMapper()