# mappers/input_mappers.py
from typing import List, Optional
from .base import BaseMapper
from foxmask.file.dtos.upload import *
from foxmask.file.graphql.schemas.upload import *

class UploadTaskInputMapper(BaseMapper):
    """上传任务输入映射器"""
    
    @staticmethod
    def initialize_input_to_dto(input_data: InitializeUploadInput) -> InitializeUploadInputDTO:
        """初始化输入转 DTO"""
        return InitializeUploadInputDTO(
            tenant_id=input_data.tenant_id, 
            created_by=input_data.created_by, 
            title=input_data.title,
            desc=input_data.desc,
            source_type=UploadSourceTypeEnum(input_data.source_type.value),
            source_paths=input_data.source_paths,
            upload_strategy=UploadStrategyEnum(input_data.upload_strategy.value),
            max_parallel_uploads=input_data.max_parallel_uploads,
            chunk_size=input_data.chunk_size,
            preserve_structure=input_data.preserve_structure,
            base_upload_path=input_data.base_upload_path,
            auto_extract_metadata=input_data.auto_extract_metadata,
            file_type_filters=[
                FileTypeEnum(ft.value) for ft in input_data.file_type_filters
            ] if input_data.file_type_filters else [],
            max_file_size=input_data.max_file_size,
            resume_task_id=input_data.resume_task_id
        )
    
    @staticmethod
    def upload_chunk_input_to_dto(input_data: UploadChunkInput) -> UploadChunkInputDTO:
        """上传分块输入转 DTO"""
        return UploadChunkInputDTO(
            tenant_id=input_data.tenant_id,
            task_id=input_data.task_id,
            file_id=input_data.file_id,
            chunk_number=input_data.chunk_number,
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
    
    @staticmethod
    def complete_upload_input_to_dto(input_data: CompleteUploadInput) -> CompleteUploadInputDTO:
        """完成上传输入转 DTO"""
        return CompleteUploadInputDTO(
            task_id=input_data.task_id,
            force_complete=input_data.force_complete or False
        )


class UploadTaskFileInputMapper(BaseMapper):
    """上传任务文件输入映射器"""
    
    @staticmethod
    def initialize_file_input_to_dto(input_data: InitializeUploadFileInput) -> InitializeUploadFileInputDTO:
        """初始化文件输入转 DTO"""
        return InitializeUploadFileInputDTO(
            original_path=input_data.original_path,
            filename=input_data.filename,
            file_size=input_data.file_size,
            file_type=FileTypeEnum(input_data.file_type.value),
            content_type=input_data.content_type,
            extension=input_data.extension,
            chunk_size=input_data.chunk_size
        )