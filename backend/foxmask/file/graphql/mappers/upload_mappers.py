# mappers/upload_mappers.py
from typing import List, Optional, Dict
from datetime import datetime
from strawberry.scalars import JSON
from .base import BaseMapper
from foxmask.file.dtos.upload import *
from foxmask.file.graphql.schemas.upload import *

class UploadTaskFileChunkMapper(BaseMapper):
    """UploadTaskFileChunk DTO 和 Schema 映射器"""
    
    @staticmethod
    def dto_to_schema(dto: UploadTaskFileChunkDTO) -> UploadTaskFileChunk:
        """DTO 转 Schema"""
        if not dto:
            return None
            
        return UploadTaskFileChunk(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            note=dto.note,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            proc_status=UploadProcStatusGql(dto.proc_status.value),
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
            max_retries=dto.max_retries
        )
    
    @staticmethod
    def schema_to_dto(schema: UploadTaskFileChunk) -> UploadTaskFileChunkDTO:
        """Schema 转 DTO"""
        if not schema:
            return None
            
        return UploadTaskFileChunkDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            master_id=schema.master_id,
            note=schema.note,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            proc_status=UploadProcStatusEnum(schema.proc_status.value),
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
            max_retries=schema.max_retries
        )
    
    @staticmethod
    def dtos_to_schemas(dtos: List[UploadTaskFileChunkDTO]) -> List[UploadTaskFileChunk]:
        """批量 DTO 转 Schema"""
        return [UploadTaskFileChunkMapper.dto_to_schema(dto) for dto in dtos] if dtos else []
    
    @staticmethod
    def schemas_to_dtos(schemas: List[UploadTaskFileChunk]) -> List[UploadTaskFileChunkDTO]:
        """批量 Schema 转 DTO"""
        return [UploadTaskFileChunkMapper.schema_to_dto(schema) for schema in schemas] if schemas else []


class UploadTaskFileMapper(BaseMapper):
    """UploadTaskFile DTO 和 Schema 映射器"""
    
    @staticmethod
    def dto_to_schema(dto: UploadTaskFileDTO) -> UploadTaskFile:
        """DTO 转 Schema"""
        if not dto:
            return None
            
        # 注意：chunks 字段在 Schema 中是 UploadTaskFileChunkConnection
        # 这里需要创建连接类型
        from .connection_mappers import UploadTaskFileChunkConnectionMapper
        
        return UploadTaskFile(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            note=dto.note,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            proc_status=UploadProcStatusGql(dto.proc_status.value),
            original_path=dto.original_path,
            storage_path=dto.storage_path,
            filename=dto.filename,
            file_size=dto.file_size,
            file_type=FileTypeGql(dto.file_type.value),
            content_type=dto.content_type,
            extension=dto.extension,
            checksum_md5=dto.checksum_md5,
            checksum_sha256=dto.checksum_sha256,
            total_chunks=dto.total_chunks,
            uploaded_chunks=dto.uploaded_chunks,
            current_chunk=dto.current_chunk,
            progress=dto.progress,
            upload_speed=dto.upload_speed,
            estimated_time_remaining=dto.estimated_time_remaining,
            extracted_metadata=BaseMapper.safe_json_conversion(dto.extracted_metadata),
            upload_started_at=dto.upload_started_at,
            upload_completed_at=dto.upload_completed_at,
            chunks=UploadTaskFileChunkConnectionMapper.create_connection(
                chunk_dtos=dto.chunks,
                total_count=len(dto.chunks) if dto.chunks else 0,
                skip=0,
                limit=len(dto.chunks) if dto.chunks else 0
            ) if dto.chunks else None
        )
    
    @staticmethod
    def schema_to_dto(schema: UploadTaskFile) -> UploadTaskFileDTO:
        """Schema 转 DTO"""
        if not schema:
            return None
            
        # 从连接类型中提取 chunks
        chunk_dtos = []
        if schema.chunks and schema.chunks.edges:
            chunk_dtos = [
                UploadTaskFileChunkMapper.schema_to_dto(edge.node) 
                for edge in schema.chunks.edges
            ]
            
        return UploadTaskFileDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            master_id=schema.master_id,
            note=schema.note,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            proc_status=UploadProcStatusEnum(schema.proc_status.value),
            original_path=schema.original_path,
            storage_path=schema.storage_path,
            filename=schema.filename,
            file_size=schema.file_size,
            file_type=FileTypeEnum(schema.file_type.value),
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
            chunks=chunk_dtos
        )
    
    @staticmethod
    def dtos_to_schemas(dtos: List[UploadTaskFileDTO]) -> List[UploadTaskFile]:
        """批量 DTO 转 Schema"""
        return [UploadTaskFileMapper.dto_to_schema(dto) for dto in dtos] if dtos else []
    
    @staticmethod
    def schemas_to_dtos(schemas: List[UploadTaskFile]) -> List[UploadTaskFileDTO]:
        """批量 Schema 转 DTO"""
        return [UploadTaskFileMapper.schema_to_dto(schema) for schema in schemas] if schemas else []


class UploadTaskMapper(BaseMapper):
    """UploadTask DTO 和 Schema 映射器"""
    
    @staticmethod
    def dto_to_schema(dto: UploadTaskDTO) -> UploadTask:
        """DTO 转 Schema"""
        if not dto:
            return None
            
        # 注意：files 字段在 Schema 中是 UploadTaskFileConnection
        from .connection_mappers import UploadTaskFileConnectionMapper
        
        return UploadTask(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            title=dto.title,
            desc=dto.desc,
            category=dto.category,
            tags=dto.tags,
            note=dto.note,
            status=StatusEnum(dto.status.value),
            visibility=VisibilityEnum(dto.visibility.value),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            archived_at=dto.archived_at,
            created_by=dto.created_by,
            allowed_users=dto.allowed_users or [],
            allowed_roles=dto.allowed_roles or [],
            proc_meta=BaseMapper.safe_json_conversion(dto.proc_meta),
            error_info=BaseMapper.safe_json_conversion(dto.error_info),
            metadata=BaseMapper.safe_json_conversion(dto.metadata),
            proc_status=UploadProcStatusGql(dto.proc_status.value),
            source_type=UploadSourceTypeGql(dto.source_type.value),
            source_paths=dto.source_paths or [],
            upload_strategy=UploadStrategyGql(dto.upload_strategy.value),
            max_parallel_uploads=dto.max_parallel_uploads,
            chunk_size=dto.chunk_size,
            preserve_structure=dto.preserve_structure,
            base_upload_path=dto.base_upload_path,
            auto_extract_metadata=dto.auto_extract_metadata,
            file_type_filters=[FileTypeGql(ft.value) for ft in dto.file_type_filters],
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
            files=UploadTaskFileConnectionMapper.create_connection(
                file_dtos=dto.files,
                total_count=len(dto.files) if dto.files else 0,
                skip=0,
                limit=len(dto.files) if dto.files else 0
            ) if dto.files else None
        )
    
    @staticmethod
    def schema_to_dto(schema: UploadTask) -> UploadTaskDTO:
        """Schema 转 DTO"""
        if not schema:
            return None
            
        # 从连接类型中提取 files
        file_dtos = []
        if schema.files and schema.files.edges:
            file_dtos = [
                UploadTaskFileMapper.schema_to_dto(edge.node) 
                for edge in schema.files.edges
            ]
            
        return UploadTaskDTO(
            uid=schema.uid,
            tenant_id=schema.tenant_id,
            title=schema.title,
            desc=schema.desc,
            category=schema.category,
            tags=schema.tags,
            note=schema.note,
            status=Status(schema.status.value),
            visibility=Visibility(schema.visibility.value),
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            archived_at=schema.archived_at,
            created_by=schema.created_by,
            allowed_users=schema.allowed_users or [],
            allowed_roles=schema.allowed_roles or [],
            proc_meta=schema.proc_meta,
            error_info=schema.error_info,
            metadata=schema.metadata,
            proc_status=UploadProcStatusEnum(schema.proc_status.value),
            source_type=UploadSourceTypeEnum(schema.source_type.value),
            source_paths=schema.source_paths or [],
            upload_strategy=UploadStrategyEnum(schema.upload_strategy.value),
            max_parallel_uploads=schema.max_parallel_uploads,
            chunk_size=schema.chunk_size,
            preserve_structure=schema.preserve_structure,
            base_upload_path=schema.base_upload_path,
            auto_extract_metadata=schema.auto_extract_metadata,
            file_type_filters=[FileTypeEnum(ft.value) for ft in schema.file_type_filters],
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
            files=file_dtos
        )
    
    @staticmethod
    def dtos_to_schemas(dtos: List[UploadTaskDTO]) -> List[UploadTask]:
        """批量 DTO 转 Schema"""
        return [UploadTaskMapper.dto_to_schema(dto) for dto in dtos] if dtos else []
    
    @staticmethod
    def schemas_to_dtos(schemas: List[UploadTask]) -> List[UploadTaskDTO]:
        """批量 Schema 转 DTO"""
        return [UploadTaskMapper.schema_to_dto(schema) for schema in schemas] if schemas else []