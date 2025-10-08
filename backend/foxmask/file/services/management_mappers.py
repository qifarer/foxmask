from typing import List, Optional, Dict, Any
from datetime import datetime
from foxmask.file.models.management import File, FileLog
from foxmask.file.dtos.management import *
from foxmask.core.enums import Status, Visibility
from foxmask.file.enums import FileTypeEnum, FileProcStatusEnum


class FileMapper:
    """文件模型映射器"""
    
    @staticmethod
    def create_dto_to_entity(dto: FileCreateDTO, uid: str) -> File:
        """FileCreateDTO 转换为 File 实体"""
        return File(
            uid=uid,
            tenant_id=dto.tenant_id,
            title=dto.title,
            desc=dto.desc,
            category=dto.category,
            tags=dto.tags or [],
            note=dto.note,
            status=dto.status,
            visibility=dto.visibility,
            created_by=dto.created_by,
            allowed_users=dto.allowed_users or [],
            allowed_roles=dto.allowed_roles or [],
            metadata=dto.metadata or {},
            # 文件特定字段
            filename=dto.filename,
            file_size=dto.file_size,
            content_type=dto.content_type,
            extension=dto.extension,
            file_type=dto.file_type,
            storage_bucket=dto.storage_bucket,
            storage_path=dto.storage_path,
            download_count=dto.download_count,
            proc_status=dto.proc_status,
        )
    
    @staticmethod
    def entity_to_response_dto(entity: File) -> FileResponseDTO:
        """File 实体转换为 FileResponseDTO"""
        return FileResponseDTO(
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            filename=entity.filename,
            file_size=entity.file_size,
            content_type=entity.content_type,
            extension=entity.extension,
            file_type=entity.file_type,
            storage_bucket=entity.storage_bucket,
            storage_path=entity.storage_path,
            download_count=entity.download_count,
            proc_status=entity.proc_status,
            title=entity.title,
            desc=entity.desc,
            category=entity.category,
            tags=entity.tags,
            note=entity.note,
            status=entity.status,
            visibility=entity.visibility,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
            created_by=entity.created_by,
            allowed_users=entity.allowed_users,
            allowed_roles=entity.allowed_roles,
            proc_meta=entity.proc_meta,
            error_info=entity.error_info,
            metadata=entity.metadata,
        )
    
    @staticmethod
    def entity_to_list_dto(entity: File) -> FileListDTO:
        """File 实体转换为 FileListDTO"""
        return FileListDTO(
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            filename=entity.filename,
            file_size=entity.file_size,
            content_type=entity.content_type,
            extension=entity.extension,
            file_type=entity.file_type,
            download_count=entity.download_count,
            proc_status=entity.proc_status,
            title=entity.title,
            status=entity.status,
            visibility=entity.visibility,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
        )
    
    @staticmethod
    def entity_to_download_dto(entity: File) -> FileDownloadDTO:
        """File 实体转换为 FileDownloadDTO"""
        return FileDownloadDTO(
            uid=entity.uid,
            filename=entity.filename,
            file_size=entity.file_size,
            content_type=entity.content_type,
            storage_bucket=entity.storage_bucket,
            storage_path=entity.storage_path,
            download_count=entity.download_count,
            title=entity.title,
            tenant_id=entity.tenant_id,
        )
    
    @staticmethod
    def entity_to_upload_response_dto(entity: File, upload_url: Optional[str] = None, expires_in: Optional[int] = None) -> FileUploadResponseDTO:
        """File 实体转换为 FileUploadResponseDTO"""
        return FileUploadResponseDTO(
            uid=entity.uid,
            filename=entity.filename,
            file_size=entity.file_size,
            content_type=entity.content_type,
            extension=entity.extension,
            file_type=entity.file_type,
            storage_bucket=entity.storage_bucket,
            storage_path=entity.storage_path,
            title=entity.title,
            tenant_id=entity.tenant_id,
            upload_url=upload_url,
            expires_in=expires_in,
        )
    
    @staticmethod
    def update_dto_to_dict(dto: FileUpdateDTO) -> Dict[str, Any]:
        """FileUpdateDTO 转换为更新字典"""
        update_data = {}
        
        # 基础文件字段
        if dto.filename is not None:
            update_data["filename"] = dto.filename
        if dto.file_size is not None:
            update_data["file_size"] = dto.file_size
        if dto.content_type is not None:
            update_data["content_type"] = dto.content_type
        if dto.extension is not None:
            update_data["extension"] = dto.extension
        if dto.file_type is not None:
            update_data["file_type"] = dto.file_type
        if dto.storage_bucket is not None:
            update_data["storage_bucket"] = dto.storage_bucket
        if dto.storage_path is not None:
            update_data["storage_path"] = dto.storage_path
        if dto.download_count is not None:
            update_data["download_count"] = dto.download_count
        if dto.proc_status is not None:
            update_data["proc_status"] = dto.proc_status
        
        # 基础模型字段
        if dto.title is not None:
            update_data["title"] = dto.title
        if dto.desc is not None:
            update_data["desc"] = dto.desc
        if dto.category is not None:
            update_data["category"] = dto.category
        if dto.tags is not None:
            update_data["tags"] = dto.tags
        if dto.note is not None:
            update_data["note"] = dto.note
        if dto.status is not None:
            update_data["status"] = dto.status
        if dto.visibility is not None:
            update_data["visibility"] = dto.visibility
        if dto.allowed_users is not None:
            update_data["allowed_users"] = dto.allowed_users
        if dto.allowed_roles is not None:
            update_data["allowed_roles"] = dto.allowed_roles
        if dto.proc_meta is not None:
            update_data["proc_meta"] = dto.proc_meta
        if dto.error_info is not None:
            update_data["error_info"] = dto.error_info
        if dto.metadata is not None:
            update_data["metadata"] = dto.metadata
        
        return update_data
    
    @staticmethod
    def entities_to_list_dtos(entities: List[File]) -> List[FileListDTO]:
        """File 实体列表转换为 FileListDTO 列表"""
        return [FileMapper.entity_to_list_dto(entity) for entity in entities]
    
    @staticmethod
    def entities_to_response_dtos(entities: List[File]) -> List[FileResponseDTO]:
        """File 实体列表转换为 FileResponseDTO 列表"""
        return [FileMapper.entity_to_response_dto(entity) for entity in entities]


class FileLogMapper:
    """文件日志模型映射器"""
    
    @staticmethod
    def create_dto_to_entity(dto: FileLogCreateDTO, uid: str) -> FileLog:
        """FileLogCreateDTO 转换为 FileLog 实体"""
        return FileLog(
            uid=uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            operation=dto.operation,
            operated_by=dto.operated_by,
            operation_time=dto.operation_time or datetime.now(),
            details=dto.details,
            ip_address=dto.ip_address,
        )
    
    @staticmethod
    def entity_to_response_dto(entity: FileLog) -> FileLogResponseDTO:
        """FileLog 实体转换为 FileLogResponseDTO"""
        return FileLogResponseDTO(
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            master_id=entity.master_id,
            operation=entity.operation,
            operated_by=entity.operated_by,
            operation_time=entity.operation_time,
            details=entity.details,
            ip_address=entity.ip_address,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            status=entity.status,
        )
    
    @staticmethod
    def entities_to_response_dtos(entities: List[FileLog]) -> List[FileLogResponseDTO]:
        """FileLog 实体列表转换为 FileLogResponseDTO 列表"""
        return [FileLogMapper.entity_to_response_dto(entity) for entity in entities]


class StatisticsMapper:
    """统计映射器"""
    
    @staticmethod
    def to_file_statistics_dto(
        tenant_id: str,
        total_files: int,
        total_size: int,
        file_type_distribution: Dict[FileTypeEnum, int],
        status_distribution: Dict[Status, int],
        proc_status_distribution: Dict[FileProcStatusEnum, int],
        visibility_distribution: Dict[Visibility, int],
    ) -> FileStatisticsDTO:
        """转换为文件统计DTO"""
        from foxmask.file.schemas.dto import FileStatisticsDTO
        
        return FileStatisticsDTO(
            tenant_id=tenant_id,
            total_files=total_files,
            total_size=total_size,
            file_type_distribution=file_type_distribution,
            status_distribution=status_distribution,
            proc_status_distribution=proc_status_distribution,
            visibility_distribution=visibility_distribution,
        )


class DTOConverter:
    """DTO转换工具类"""
    
    @staticmethod
    def file_create_input_to_dto(input_data: Any) -> FileCreateDTO:
        """GraphQL输入类型转换为FileCreateDTO"""
        # 这里需要根据实际的GraphQL输入类型进行调整
        return FileCreateDTO(
            filename=input_data.filename,
            file_size=input_data.file_size,
            storage_bucket=input_data.storage_bucket,
            storage_path=input_data.storage_path,
            extension=input_data.extension,
            title=input_data.title,
            tenant_id=input_data.tenant_id,
            content_type=input_data.content_type,
            file_type=input_data.file_type,
            proc_status=input_data.proc_status,
            download_count=input_data.download_count,
            desc=input_data.desc,
            category=input_data.category,
            tags=input_data.tags or [],
            note=input_data.note,
            status=input_data.status,
            visibility=input_data.visibility,
            created_by=input_data.created_by,
            allowed_users=input_data.allowed_users or [],
            allowed_roles=input_data.allowed_roles or [],
            metadata=input_data.metadata or {},
        )
    
    @staticmethod
    def file_update_input_to_dto(input_data: Any) -> FileUpdateDTO:
        """GraphQL输入类型转换为FileUpdateDTO"""
        return FileUpdateDTO(
            filename=input_data.filename,
            file_size=input_data.file_size,
            content_type=input_data.content_type,
            extension=input_data.extension,
            file_type=input_data.file_type,
            storage_bucket=input_data.storage_bucket,
            storage_path=input_data.storage_path,
            download_count=input_data.download_count,
            proc_status=input_data.proc_status,
            title=input_data.title,
            desc=input_data.desc,
            category=input_data.category,
            tags=input_data.tags,
            note=input_data.note,
            status=input_data.status,
            visibility=input_data.visibility,
            allowed_users=input_data.allowed_users,
            allowed_roles=input_data.allowed_roles,
            proc_meta=input_data.proc_meta,
            error_info=input_data.error_info,
            metadata=input_data.metadata,
        )


# 创建映射器实例
file_mapper = FileMapper()
file_log_mapper = FileLogMapper()
statistics_mapper = StatisticsMapper()
dto_converter = DTOConverter()