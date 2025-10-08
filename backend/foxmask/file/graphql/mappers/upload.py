from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict
import base64

from foxmask.core.enums import *
from foxmask.core.logger import logger
from foxmask.file.dtos.upload import *
from foxmask.file.enums import *
from foxmask.file.graphql.schemas.upload import *
from foxmask.utils.helpers import convert_upload_to_string, get_current_timestamp


class UploadMapper:
    """DTO 和 GraphQL Schema 映射转换器"""
    
    # ============================
    # Enum 映射方法 (DTO -> GraphQL)
    # ============================
    
    @staticmethod
    def _map_proc_status_enum(dto_enum: Optional[UploadProcStatusEnum]):
        """处理状态枚举映射"""
        from ..schemas.enums import UploadProcStatusGql
        if dto_enum is None:
            return UploadProcStatusGql.PENDING
            
        mapping = {
            UploadProcStatusEnum.PENDING: UploadProcStatusGql.PENDING,
            UploadProcStatusEnum.PROCESSING: UploadProcStatusGql.PROCESSING,
            UploadProcStatusEnum.COMPLETED: UploadProcStatusGql.COMPLETED,
            UploadProcStatusEnum.FAILED: UploadProcStatusGql.FAILED,
            UploadProcStatusEnum.CANCELLED: UploadProcStatusGql.CANCELLED,
        }
        return mapping.get(dto_enum, UploadProcStatusGql.PENDING)
    
    @staticmethod
    def _map_file_type_enum(dto_enum: Optional[FileTypeEnum]):
        """文件类型枚举映射"""
        from ..schemas.enums import FileTypeGql
        if dto_enum is None:
            return FileTypeGql.OTHER
            
        mapping = {
            FileTypeEnum.IMAGE: FileTypeGql.IMAGE,
            FileTypeEnum.VIDEO: FileTypeGql.VIDEO,
            FileTypeEnum.AUDIO: FileTypeGql.AUDIO,
            FileTypeEnum.DOCUMENT: FileTypeGql.DOCUMENT,
            FileTypeEnum.ARCHIVE: FileTypeGql.ARCHIVE,
            FileTypeEnum.OTHER: FileTypeGql.OTHER,
        }
        return mapping.get(dto_enum, FileTypeGql.OTHER)
    
    @staticmethod
    def _map_source_type_enum(dto_enum: Optional[UploadSourceTypeEnum]):
        """上传源类型枚举映射"""
        from ..schemas.enums import UploadSourceTypeGql
        if dto_enum is None:
            return UploadSourceTypeGql.SINGLE_FILE
            
        mapping = {
            UploadSourceTypeEnum.SINGLE_FILE: UploadSourceTypeGql.SINGLE_FILE,
            UploadSourceTypeEnum.MULTIPLE_FILES: UploadSourceTypeGql.MULTIPLE_FILES,
            UploadSourceTypeEnum.SINGLE_DIRECTORY: UploadSourceTypeGql.SINGLE_DIRECTORY,
            UploadSourceTypeEnum.MULTIPLE_DIRECTORIES: UploadSourceTypeGql.MULTIPLE_DIRECTORIES,
        }
        return mapping.get(dto_enum, UploadSourceTypeGql.SINGLE_FILE)
    
    @staticmethod
    def _map_strategy_enum(dto_enum: Optional[UploadStrategyEnum]):
        """上传策略枚举映射"""
        from ..schemas.enums import UploadStrategyGql
        if dto_enum is None:
            return UploadStrategyGql.SEQUENTIAL
            
        mapping = {
            UploadStrategyEnum.SEQUENTIAL: UploadStrategyGql.SEQUENTIAL,
            UploadStrategyEnum.PARALLEL: UploadStrategyGql.PARALLEL,
        }
        return mapping.get(dto_enum, UploadStrategyGql.SEQUENTIAL)
    
    @staticmethod
    def _map_status_enum(dto_enum: Optional[Status]):
        """状态枚举映射"""
        from foxmask.core.schema import StatusEnum
        if dto_enum is None:
            return StatusEnum.DRAFT
            
        mapping = {
            Status.DRAFT: StatusEnum.DRAFT,
            Status.ACTIVE: StatusEnum.ACTIVE,
            Status.ARCHIVED: StatusEnum.ARCHIVED,
        }
        return mapping.get(dto_enum, StatusEnum.DRAFT)
    
    @staticmethod
    def _map_visibility_enum(dto_enum: Optional[Visibility]):
        """可见性枚举映射"""
        from foxmask.core.schema import VisibilityEnum
        if dto_enum is None:
            return VisibilityEnum.PUBLIC
            
        mapping = {
            Visibility.PUBLIC: VisibilityEnum.PUBLIC,
            Visibility.PRIVATE: VisibilityEnum.PRIVATE,
            Visibility.TENANT: VisibilityEnum.TENANT,
        }
        return mapping.get(dto_enum, VisibilityEnum.PUBLIC)

    # ============================
    # 反向 Enum 映射 (GraphQL -> DTO)
    # ============================
    
    @staticmethod
    def _map_proc_status_enum_reverse(schema_enum):
        """处理状态枚举反向映射"""
        from ..schemas.enums import UploadProcStatusGql
        if schema_enum is None:
            return UploadProcStatusEnum.PENDING
            
        mapping = {
            UploadProcStatusGql.PENDING: UploadProcStatusEnum.PENDING,
            UploadProcStatusGql.PROCESSING: UploadProcStatusEnum.PROCESSING,
            UploadProcStatusGql.COMPLETED: UploadProcStatusEnum.COMPLETED,
            UploadProcStatusGql.FAILED: UploadProcStatusEnum.FAILED,
            UploadProcStatusGql.CANCELLED: UploadProcStatusEnum.CANCELLED,
        }
        return mapping.get(schema_enum, UploadProcStatusEnum.PENDING)
    
    @staticmethod
    def _map_file_type_enum_reverse(schema_enum):
        """文件类型枚举反向映射"""
        from ..schemas.enums import FileTypeGql
        if schema_enum is None:
            return FileTypeEnum.OTHER
            
        mapping = {
            FileTypeGql.IMAGE: FileTypeEnum.IMAGE,
            FileTypeGql.VIDEO: FileTypeEnum.VIDEO,
            FileTypeGql.AUDIO: FileTypeEnum.AUDIO,
            FileTypeGql.DOCUMENT: FileTypeEnum.DOCUMENT,
            FileTypeGql.ARCHIVE: FileTypeEnum.ARCHIVE,
            FileTypeGql.OTHER: FileTypeEnum.OTHER,
        }
        return mapping.get(schema_enum, FileTypeEnum.OTHER)
    
    @staticmethod
    def _map_source_type_enum_reverse(schema_enum):
        """上传源类型枚举反向映射"""
        from ..schemas.enums import UploadSourceTypeGql
        if schema_enum is None:
            return UploadSourceTypeEnum.SINGLE_FILE
            
        mapping = {
            UploadSourceTypeGql.SINGLE_FILE: UploadSourceTypeEnum.SINGLE_FILE,
            UploadSourceTypeGql.MULTIPLE_FILES: UploadSourceTypeEnum.MULTIPLE_FILES,
            UploadSourceTypeGql.SINGLE_DIRECTORY: UploadSourceTypeEnum.SINGLE_DIRECTORY,
            UploadSourceTypeGql.MULTIPLE_DIRECTORIES: UploadSourceTypeEnum.MULTIPLE_DIRECTORIES,
        }
        return mapping.get(schema_enum, UploadSourceTypeEnum.SINGLE_FILE)
    
    @staticmethod
    def _map_strategy_enum_reverse(schema_enum):
        """上传策略枚举反向映射"""
        from ..schemas.enums import UploadStrategyGql
        if schema_enum is None:
            return UploadStrategyEnum.SEQUENTIAL
            
        mapping = {
            UploadStrategyGql.SEQUENTIAL: UploadStrategyEnum.SEQUENTIAL,
            UploadStrategyGql.PARALLEL: UploadStrategyEnum.PARALLEL,
        }
        return mapping.get(schema_enum, UploadStrategyEnum.SEQUENTIAL)
    
    @staticmethod
    def _map_status_enum_reverse(schema_enum):
        """状态枚举反向映射"""
        from foxmask.core.schema import StatusEnum
        if schema_enum is None:
            return Status.DRAFT
            
        mapping = {
            StatusEnum.DRAFT: Status.DRAFT,
            StatusEnum.ACTIVE: Status.ACTIVE,
            StatusEnum.ARCHIVED: Status.ARCHIVED,
        }
        return mapping.get(schema_enum, Status.DRAFT)
    
    @staticmethod
    def _map_visibility_enum_reverse(schema_enum):
        """可见性枚举反向映射"""
        from foxmask.core.schema import VisibilityEnum
        if schema_enum is None:
            return Visibility.PUBLIC
            
        mapping = {
            VisibilityEnum.PUBLIC: Visibility.PUBLIC,
            VisibilityEnum.PRIVATE: Visibility.PRIVATE,
            VisibilityEnum.TENANT: Visibility.TENANT,
        }
        return mapping.get(schema_enum, Visibility.PUBLIC)

    # ============================
    # DTO -> GraphQL Schema 转换方法
    # ============================
    
    @staticmethod
    def error_dto_to_schema(dto: ErrorDTO) -> Error:
        """ErrorDTO 转 Error"""
        return Error(
            message=dto.message,
            code=dto.code,
            field=dto.field
        )
    
    @staticmethod
    def page_info_dto_to_schema(dto: PageInfoDTO) -> PageInfo:
        """PageInfoDTO 转 PageInfo"""
        return PageInfo(
            has_next_page=dto.has_next_page,
            has_previous_page=dto.has_previous_page,
            total_count=dto.total_count,
            current_page=dto.current_page,
            total_pages=dto.total_pages
        )
    
    @staticmethod
    def upload_task_file_chunk_dto_to_schema(dto: UploadTaskFileChunkDTO) -> UploadTaskFileChunk:
        """UploadTaskFileChunkDTO 转 UploadTaskFileChunk"""
        return UploadTaskFileChunk(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            file_id=dto.file_id,
            chunk_number=dto.chunk_number,
            chunk_size=dto.chunk_size,
            start_byte=dto.start_byte,
            end_byte=dto.end_byte,
            is_final_chunk=dto.is_final_chunk,
            minio_bucket=dto.minio_bucket,
            minio_object_name=dto.minio_object_name,
            minio_etag=dto.minio_etag,
            checksum_md5=dto.checksum_md5,
            checksum_sha256=dto.checksum_sha256,
            retry_count=dto.retry_count,
            max_retries=dto.max_retries,
            note=dto.note,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            proc_status=UploadMapper._map_proc_status_enum(dto.proc_status)
        )
    
    @staticmethod
    def upload_task_file_dto_to_schema(dto: UploadTaskFileDTO) -> UploadTaskFile:
        """UploadTaskFileDTO 转 UploadTaskFile"""
        chunks = None
        if dto.chunks:
            chunks = [UploadMapper.upload_task_file_chunk_dto_to_schema(chunk) for chunk in dto.chunks]
        
        return UploadTaskFile(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            original_path=dto.original_path,
            storage_path=dto.storage_path,
            filename=dto.filename,
            file_size=dto.file_size,
            file_type=UploadMapper._map_file_type_enum(dto.file_type),
            content_type=dto.content_type,
            extension=dto.extension,
            minio_bucket=dto.minio_bucket,
            minio_object_name=dto.minio_object_name,
            minio_etag=dto.minio_etag,
            checksum_md5=dto.checksum_md5,
            checksum_sha256=dto.checksum_sha256,
            total_chunks=dto.total_chunks,
            uploaded_chunks=dto.uploaded_chunks,
            current_chunk=dto.current_chunk,
            progress=dto.progress,
            upload_speed=dto.upload_speed,
            estimated_time_remaining=dto.estimated_time_remaining,
            extracted_metadata=dto.extracted_metadata,
            upload_started_at=dto.upload_started_at,
            upload_completed_at=dto.upload_completed_at,
            note=dto.note,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            proc_status=UploadMapper._map_proc_status_enum(dto.proc_status),
            chunks=chunks
        )
    
    @staticmethod
    def upload_task_dto_to_schema(dto: UploadTaskDTO) -> UploadTask:
        """UploadTaskDTO 转 UploadTask"""
        files = None
        if dto.files:
            files = [UploadMapper.upload_task_file_dto_to_schema(file_dto) for file_dto in dto.files]
        
        file_type_filters = [UploadMapper._map_file_type_enum(ft) for ft in (dto.file_type_filters or [])]
        
        return UploadTask(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            title=dto.title,
            desc=dto.desc,
            category=dto.category,
            tags=dto.tags,
            note=dto.note,
            status=UploadMapper._map_status_enum(dto.status),
            visibility=UploadMapper._map_visibility_enum(dto.visibility),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            archived_at=dto.archived_at,
            created_by=dto.created_by,
            allowed_users=dto.allowed_users or [],
            allowed_roles=dto.allowed_roles or [],
            proc_meta=dto.proc_meta,
            error_info=dto.error_info,
            metadata=dto.metadata,
            proc_status=UploadMapper._map_proc_status_enum(dto.proc_status),
            source_type=UploadMapper._map_source_type_enum(dto.source_type),
            source_paths=dto.source_paths or [],
            upload_strategy=UploadMapper._map_strategy_enum(dto.upload_strategy),
            max_parallel_uploads=dto.max_parallel_uploads,
            chunk_size=dto.chunk_size,
            preserve_structure=dto.preserve_structure,
            base_upload_path=dto.base_upload_path,
            auto_extract_metadata=dto.auto_extract_metadata,
            file_type_filters=file_type_filters,
            max_file_size=dto.max_file_size,
            discovered_files=dto.discovered_files,
            processing_files=dto.processing_files,
            total_files=dto.total_files,
            completed_files=dto.completed_files,
            failed_files=dto.failed_files,
            total_size=dto.total_size,
            uploaded_size=dto.uploaded_size,
            discovery_started_at=dto.discovery_started_at,
            discovery_completed_at=dto.discovery_completed_at,
            files=files
        )
    
    @staticmethod
    def file_upload_progress_dto_to_schema(dto: FileUploadProgressDTO) -> FileUploadProgress:
        """FileUploadProgressDTO 转 FileUploadProgress"""
        return FileUploadProgress(
            file_id=dto.file_id,
            filename=dto.filename,
            progress=dto.progress,
            uploaded_chunks=dto.uploaded_chunks,
            total_chunks=dto.total_chunks,
            upload_speed=dto.upload_speed,
            estimated_time_remaining=dto.estimated_time_remaining,
            current_chunk=dto.current_chunk
        )
    
    @staticmethod
    def upload_progress_dto_to_schema(dto: UploadProgressDTO) -> UploadProgress:
        """UploadProgressDTO 转 UploadProgress"""
        current_uploading_files = None
        if dto.current_uploading_files:
            current_uploading_files = [
                UploadMapper.file_upload_progress_dto_to_schema(file_progress)
                for file_progress in dto.current_uploading_files
            ]
        
        return UploadProgress(
            task_id=dto.task_id,
            total_files=dto.total_files,
            completed_files=dto.completed_files,
            failed_files=dto.failed_files,
            progress_percentage=dto.progress_percentage,
            uploaded_size=dto.uploaded_size,
            total_size=dto.total_size,
            average_upload_speed=dto.average_upload_speed,
            estimated_time_remaining=dto.estimated_time_remaining,
            current_uploading_files=current_uploading_files
        )
    
    @staticmethod
    def upload_task_stats_dto_to_schema(dto: UploadTaskStatsDTO) -> UploadTaskStats:
        """UploadTaskStatsDTO 转 UploadTaskStats"""
        return UploadTaskStats(
            total_tasks=dto.total_tasks,
            active_tasks=dto.active_tasks,
            completed_tasks=dto.completed_tasks,
            failed_tasks=dto.failed_tasks,
            total_files=dto.total_files,
            total_size=dto.total_size,
            average_upload_speed=dto.average_upload_speed,
            success_rate=dto.success_rate
        )
    
    @staticmethod
    def upload_resume_info_dto_to_schema(dto: UploadResumeInfoDTO) -> UploadResumeInfo:
        """UploadResumeInfoDTO 转 UploadResumeInfo"""
        return UploadResumeInfo(
            task_id=dto.task_id,
            file_id=dto.file_id,
            uploaded_chunks=dto.uploaded_chunks,
            total_chunks=dto.total_chunks,
            next_chunk_number=dto.next_chunk_number,
            file_size=dto.file_size,
            uploaded_size=dto.uploaded_size,
            progress=dto.progress
        )

    # ============================
    # GraphQL Schema -> DTO 转换方法
    # ============================
    
    @staticmethod
    def upload_task_file_chunk_schema_to_dto(schema: UploadTaskFileChunk) -> UploadTaskFileChunkDTO:
        """UploadTaskFileChunk 转 UploadTaskFileChunkDTO"""
        return UploadTaskFileChunkDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            master_id=schema.master_id,
            file_id=schema.file_id,
            chunk_number=schema.chunk_number,
            chunk_size=schema.chunk_size,
            start_byte=schema.start_byte,
            end_byte=schema.end_byte,
            is_final_chunk=schema.is_final_chunk,
            minio_bucket=schema.minio_bucket,
            minio_object_name=schema.minio_object_name,
            minio_etag=schema.minio_etag,
            checksum_md5=schema.checksum_md5,
            checksum_sha256=schema.checksum_sha256,
            retry_count=schema.retry_count,
            max_retries=schema.max_retries,
            note=schema.note,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            proc_status=UploadMapper._map_proc_status_enum_reverse(schema.proc_status)
        )
    
    @staticmethod
    def upload_task_file_schema_to_dto(schema: UploadTaskFile) -> UploadTaskFileDTO:
        """UploadTaskFile 转 UploadTaskFileDTO"""
        chunks = None
        if schema.chunks:
            chunks = [UploadMapper.upload_task_file_chunk_schema_to_dto(chunk) for chunk in schema.chunks]
        
        return UploadTaskFileDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            master_id=schema.master_id,
            original_path=schema.original_path,
            storage_path=schema.storage_path,
            filename=schema.filename,
            file_size=schema.file_size,
            file_type=UploadMapper._map_file_type_enum_reverse(schema.file_type),
            content_type=schema.content_type,
            extension=schema.extension,
            checksum_md5=schema.checksum_md5,
            checksum_sha256=schema.checksum_sha256,
            total_chunks=schema.total_chunks,
            uploaded_chunks=schema.uploaded_chunks,
            current_chunk=schema.current_chunk,
            progress=schema.progress,
            upload_speed=schema.upload_speed,
            estimated_time_remaining=schema.estimated_time_remaining,
            extracted_metadata=schema.extracted_metadata,
            upload_started_at=schema.upload_started_at,
            upload_completed_at=schema.upload_completed_at,
            note=schema.note,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            proc_status=UploadMapper._map_proc_status_enum_reverse(schema.proc_status),
            chunks=chunks
        )
    
    @staticmethod
    def upload_task_schema_to_dto(schema: UploadTask) -> UploadTaskDTO:
        """UploadTask 转 UploadTaskDTO"""
        files = None
        if schema.files:
            files = [UploadMapper.upload_task_file_schema_to_dto(file_schema) for file_schema in schema.files]
        
        file_type_filters = [UploadMapper._map_file_type_enum_reverse(ft) for ft in (schema.file_type_filters or [])]
        
        return UploadTaskDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            title=schema.title,
            desc=schema.desc,
            category=schema.category,
            tags=schema.tags,
            note=schema.note,
            status=UploadMapper._map_status_enum_reverse(schema.status),
            visibility=UploadMapper._map_visibility_enum_reverse(schema.visibility),
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            archived_at=schema.archived_at,
            created_by=schema.created_by,
            allowed_users=schema.allowed_users or [],
            allowed_roles=schema.allowed_roles or [],
            proc_meta=schema.proc_meta,
            error_info=schema.error_info,
            metadata=schema.metadata,
            proc_status=UploadMapper._map_proc_status_enum_reverse(schema.proc_status),
            source_type=UploadMapper._map_source_type_enum_reverse(schema.source_type),
            source_paths=schema.source_paths or [],
            upload_strategy=UploadMapper._map_strategy_enum_reverse(schema.upload_strategy),
            max_parallel_uploads=schema.max_parallel_uploads,
            chunk_size=schema.chunk_size,
            preserve_structure=schema.preserve_structure,
            base_upload_path=schema.base_upload_path,
            auto_extract_metadata=schema.auto_extract_metadata,
            file_type_filters=file_type_filters,
            max_file_size=schema.max_file_size,
            discovered_files=schema.discovered_files,
            processing_files=schema.processing_files,
            total_files=schema.total_files,
            completed_files=schema.completed_files,
            failed_files=schema.failed_files,
            total_size=schema.total_size,
            uploaded_size=schema.uploaded_size,
            discovery_started_at=schema.discovery_started_at,
            discovery_completed_at=schema.discovery_completed_at,
            files=files
        )

    # ============================
    # 响应类型转换
    # ============================
    
    @staticmethod
    def base_response_dto_to_schema(dto: BaseResponseDTO, data_field: str = None, data_value=None):
        """BaseResponseDTO 转 BaseResponse"""
        errors = None
        if dto.errors:
            errors = [UploadMapper.error_dto_to_schema(error) for error in dto.errors]
        
        response_data = {
            "success": dto.success,
            "errors": errors
        }
        
        if data_field and data_value is not None:
            response_data[data_field] = data_value
        
        return response_data
    
    @staticmethod
    def initialize_upload_response_dto_to_schema(dto: InitializeUploadResponseDTO) -> InitializeUploadResponse:
        """InitializeUploadResponseDTO 转 InitializeUploadResponse"""
        data = None
        if dto.data:
            data = UploadMapper.upload_task_dto_to_schema(dto.data)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        return InitializeUploadResponse(**base_data)
    
    @staticmethod
    def upload_chunk_response_dto_to_schema(dto: UploadChunkResponseDTO) -> UploadChunkResponse:
        """UploadChunkResponseDTO 转 UploadChunkResponse"""
        data = None
        if dto.data:
            data = UploadMapper.upload_task_file_chunk_dto_to_schema(dto.data)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        base_data.update({
            "next_chunk": dto.next_chunk,
            "progress": dto.progress,
            "is_completed": dto.is_completed
        })
        return UploadChunkResponse(**base_data)
    
    @staticmethod
    def complete_upload_response_dto_to_schema(dto: CompleteUploadResponseDTO) -> CompleteUploadResponse:
        """CompleteUploadResponseDTO 转 CompleteUploadResponse"""
        data = None
        if dto.data:
            data = UploadMapper.upload_task_file_dto_to_schema(dto.data)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        return CompleteUploadResponse(**base_data)
    
    @staticmethod
    def get_upload_task_response_dto_to_schema(dto: GetUploadTaskResponseDTO) -> GetUploadTaskResponse:
        """GetUploadTaskResponseDTO 转 GetUploadTaskResponse"""
        data = None
        if dto.data:
            data = UploadMapper.upload_task_dto_to_schema(dto.data)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        return GetUploadTaskResponse(**base_data)
    
    @staticmethod
    def list_upload_tasks_response_dto_to_schema(dto: ListUploadTasksResponseDTO) -> ListUploadTasksResponse:
        """ListUploadTasksResponseDTO 转 ListUploadTasksResponse"""
        data = None
        if dto.data:
            data = [UploadMapper.upload_task_dto_to_schema(task) for task in dto.data]
        
        pagination = None
        if dto.pagination:
            pagination = UploadMapper.page_info_dto_to_schema(dto.pagination)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        base_data["pagination"] = pagination
        return ListUploadTasksResponse(**base_data)
    
    @staticmethod
    def list_upload_task_files_response_dto_to_schema(dto: ListUploadTaskFilesResponseDTO) -> ListUploadTaskFilesResponse:
        """ListUploadTaskFilesResponseDTO 转 ListUploadTaskFilesResponse"""
        data = None
        if dto.data:
            data = [UploadMapper.upload_task_file_dto_to_schema(file) for file in dto.data]
        
        pagination = None
        if dto.pagination:
            pagination = UploadMapper.page_info_dto_to_schema(dto.pagination)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        base_data["pagination"] = pagination
        return ListUploadTaskFilesResponse(**base_data)
    
    @staticmethod
    def list_upload_task_file_chunks_response_dto_to_schema(dto: ListUploadTaskFileChunksResponseDTO) -> ListUploadTaskFileChunksResponse:
        """ListUploadTaskFileChunksResponseDTO 转 ListUploadTaskFileChunksResponse"""
        data = None
        if dto.data:
            data = [UploadMapper.upload_task_file_chunk_dto_to_schema(chunk) for chunk in dto.data]
        
        pagination = None
        if dto.pagination:
            pagination = UploadMapper.page_info_dto_to_schema(dto.pagination)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        base_data["pagination"] = pagination
        return ListUploadTaskFileChunksResponse(**base_data)
    
    @staticmethod
    def resume_upload_response_dto_to_schema(dto: ResumeUploadResponseDTO) -> ResumeUploadResponse:
        """ResumeUploadResponseDTO 转 ResumeUploadResponse"""
        data = None
        if dto.data:
            data = UploadMapper.upload_task_dto_to_schema(dto.data)
        
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        base_data.update({
            "resumed_files": dto.resumed_files,
            "total_files_to_resume": dto.total_files_to_resume
        })
        return ResumeUploadResponse(**base_data)
    
    @staticmethod
    def upload_progress_response_dto_to_schema(dto: BaseResponseDTO, progress_dto: UploadProgressDTO) -> UploadProgressResponse:
        """UploadProgressDTO 转 UploadProgressResponse"""
        data = UploadMapper.upload_progress_dto_to_schema(progress_dto)
        base_data = UploadMapper.base_response_dto_to_schema(dto, "data", data)
        return UploadProgressResponse(**base_data)

    # ============================
    # 输入类型转换 (GraphQL Input -> DTO)
    # ============================
    
    @staticmethod
    def initialize_upload_input_to_dto(input_data, tenant_id: str = None, created_by: str = None) -> InitializeUploadInputDTO:
        """InitializeUploadInput 转 InitializeUploadInputDTO"""
        files = None
        if input_data.files:
            files = [
                InitializeUploadFileInputDTO(
                    original_path=file.original_path,
                    filename=file.filename,
                    file_size=file.file_size,
                    file_type=UploadMapper._map_file_type_enum_reverse(file.file_type),
                    content_type=file.content_type,
                    extension=file.extension,
                    chunk_size=file.chunk_size
                )
                for file in input_data.files
            ]
        
        file_type_filters = [UploadMapper._map_file_type_enum_reverse(ft) for ft in (input_data.file_type_filters or [])]
        
        return InitializeUploadInputDTO(
            tenant_id=tenant_id or input_data.tenant_id,
            created_by=created_by or input_data.created_by,
            title=input_data.title,
            source_type=UploadMapper._map_source_type_enum_reverse(input_data.source_type),
            source_paths=input_data.source_paths or [],
            upload_strategy=UploadMapper._map_strategy_enum_reverse(input_data.upload_strategy),
            chunk_size=input_data.chunk_size,
            desc=input_data.desc,
            max_parallel_uploads=input_data.max_parallel_uploads,
            preserve_structure=input_data.preserve_structure,
            base_upload_path=input_data.base_upload_path,
            auto_extract_metadata=input_data.auto_extract_metadata,
            file_type_filters=file_type_filters,
            max_file_size=input_data.max_file_size,
            files=files,
            resume_task_id=input_data.resume_task_id
        )
    
    @staticmethod
    def upload_chunk_input_to_dto(input_data, tenant_id: str = None) -> UploadChunkInputDTO:
        """UploadChunkInput 转 UploadChunkInputDTO - 处理 Upload 类型"""
        try:
            chunk_data_str = convert_upload_to_string(input_data.chunk_data)
            return UploadChunkInputDTO(
                tenant_id=tenant_id,
                task_id=input_data.task_id,
                file_id=input_data.file_id,
                chunk_number=input_data.chunk_number,
                chunk_data=chunk_data_str,
                chunk_size=input_data.chunk_size,
                start_byte=input_data.start_byte,
                end_byte=input_data.end_byte,
                is_final_chunk=input_data.is_final_chunk,
                minio_bucket=input_data.minio_bucket,
                minio_object_name=input_data.minio_object_name,
                checksum_md5=input_data.checksum_md5,
                checksum_sha256=input_data.checksum_sha256,
                max_retries=input_data.max_retries
            )
        except Exception as e:
            logger.error(f"转换 UploadChunkInput 到 DTO 失败: {e}")
            raise
    
    @staticmethod
    def complete_upload_input_to_dto(input_data) -> CompleteUploadInputDTO:
        """CompleteUploadInput 转 CompleteUploadInputDTO"""
        return CompleteUploadInputDTO(
            task_id=input_data.task_id,
            file_id=input_data.file_id,
            checksum_md5=input_data.checksum_md5,
            checksum_sha256=input_data.checksum_sha256
        )
    
    @staticmethod
    def resume_upload_input_to_dto(input_data, tenant_id: str, created_by: str) -> ResumeUploadInputDTO:
        """ResumeUploadInput 转 ResumeUploadInputDTO"""
        return ResumeUploadInputDTO(
            task_id=input_data.task_id,
            tenant_id=tenant_id,
            created_by=created_by
        )
    
    @staticmethod
    def upload_task_query_input_to_dto(input_data, tenant_id: str) -> UploadTaskQueryDTO:
        """UploadTaskQueryInput 转 UploadTaskQueryDTO"""
        return UploadTaskQueryDTO(
            tenant_id=tenant_id,
            task_id=input_data.task_id,
            created_by=input_data.created_by,
            status=UploadMapper._map_status_enum_reverse(input_data.status) if input_data.status else None,
            proc_status=UploadMapper._map_proc_status_enum_reverse(input_data.proc_status) if input_data.proc_status else None,
            source_type=UploadMapper._map_source_type_enum_reverse(input_data.source_type) if input_data.source_type else None,
            tags=input_data.tags,
            category=input_data.category,
            created_at_start=input_data.created_at_start,
            created_at_end=input_data.created_at_end
        )
    
    @staticmethod
    def upload_task_file_query_input_to_dto(input_data, tenant_id: str) -> UploadTaskFileQueryDTO:
        """UploadTaskFileQueryInput 转 UploadTaskFileQueryDTO"""
        return UploadTaskFileQueryDTO(
            tenant_id=tenant_id,
            task_id=input_data.task_id,
            file_id=input_data.file_id,
            proc_status=UploadMapper._map_proc_status_enum_reverse(input_data.proc_status) if input_data.proc_status else None,
            file_type=UploadMapper._map_file_type_enum_reverse(input_data.file_type) if input_data.file_type else None
        )
    
    @staticmethod
    def upload_task_file_chunk_query_input_to_dto(input_data, tenant_id: str) -> UploadTaskFileChunkQueryDTO:
        """UploadTaskFileChunkQueryInput 转 UploadTaskFileChunkQueryDTO"""
        return UploadTaskFileChunkQueryDTO(
            tenant_id=tenant_id,
            file_id=input_data.file_id,
            chunk_number=input_data.chunk_number,
            proc_status=UploadMapper._map_proc_status_enum_reverse(input_data.proc_status) if input_data.proc_status else None
        )

    # ============================
    # 批量转换方法
    # ============================
    
    @staticmethod
    def upload_task_dto_list_to_schema(dto_list: List[UploadTaskDTO]) -> List[UploadTask]:
        """UploadTaskDTO 列表转 UploadTask 列表"""
        return [UploadMapper.upload_task_dto_to_schema(dto) for dto in dto_list]
    
    @staticmethod
    def upload_task_file_dto_list_to_schema(dto_list: List[UploadTaskFileDTO]) -> List[UploadTaskFile]:
        """UploadTaskFileDTO 列表转 UploadTaskFile 列表"""
        return [UploadMapper.upload_task_file_dto_to_schema(dto) for dto in dto_list]
    
    @staticmethod
    def upload_task_file_chunk_dto_list_to_schema(dto_list: List[UploadTaskFileChunkDTO]) -> List[UploadTaskFileChunk]:
        """UploadTaskFileChunkDTO 列表转 UploadTaskFileChunk 列表"""
        return [UploadMapper.upload_task_file_chunk_dto_to_schema(dto) for dto in dto_list]

    @staticmethod
    def upload_task_schema_list_to_dto(schema_list: List[UploadTask]) -> List[UploadTaskDTO]:
        """UploadTask 列表转 UploadTaskDTO 列表"""
        return [UploadMapper.upload_task_schema_to_dto(schema) for schema in schema_list]
    
    @staticmethod
    def upload_task_file_schema_list_to_dto(schema_list: List[UploadTaskFile]) -> List[UploadTaskFileDTO]:
        """UploadTaskFile 列表转 UploadTaskFileDTO 列表"""
        return [UploadMapper.upload_task_file_schema_to_dto(schema) for schema in schema_list]
    
    @staticmethod
    def upload_task_file_chunk_schema_list_to_dto(schema_list: List[UploadTaskFileChunk]) -> List[UploadTaskFileChunkDTO]:
        """UploadTaskFileChunk 列表转 UploadTaskFileChunkDTO 列表"""
        return [UploadMapper.upload_task_file_chunk_schema_to_dto(schema) for schema in schema_list]