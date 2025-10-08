from typing import List, Optional, Dict, Any
from datetime import datetime
from foxmask.file.dtos.management import *
from foxmask.file.graphql.schemas.management import *

class SchemaToDTOMapper:
    """GraphQL Schema 到 DTO 映射器"""
    
    @staticmethod
    def file_create_input_to_dto(input_data: FileCreateInput) -> FileCreateDTO:
        """FileCreateInput 转换为 FileCreateDTO"""
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
    def file_update_input_to_dto(input_data: FileUpdateInput) -> FileUpdateDTO:
        """FileUpdateInput 转换为 FileUpdateDTO"""
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
    
    @staticmethod
    def file_query_input_to_dto(input_data: FileQueryInput) -> FileQueryDTO:
        """FileQueryInput 转换为 FileQueryDTO"""
        return FileQueryDTO(
            tenant_id=input_data.tenant_id,
            filename=input_data.filename,
            title=input_data.title,
            file_type=input_data.file_type,
            proc_status=input_data.proc_status,
            content_type=input_data.content_type,
            category=input_data.category,
            tags=input_data.tags,
            status=input_data.status,
            visibility=input_data.visibility,
            created_by=input_data.created_by,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            page=input_data.page,
            page_size=input_data.page_size,
        )
    
    @staticmethod
    def file_search_input_to_dto(input_data: FileSearchInput) -> FileSearchDTO:
        """FileSearchInput 转换为 FileSearchDTO"""
        return FileSearchDTO(
            tenant_id=input_data.tenant_id,
            keyword=input_data.keyword,
            filename=input_data.filename,
            title=input_data.title,
            desc=input_data.desc,
            category=input_data.category,
            tags=input_data.tags,
            file_type=input_data.file_type,
            status=input_data.status,
            visibility=input_data.visibility,
            created_by=input_data.created_by,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            page=input_data.page,
            page_size=input_data.page_size,
        )
    
    @staticmethod
    def file_bulk_update_input_to_dto(input_data: FileBulkUpdateInput) -> FileBulkUpdateDTO:
        """FileBulkUpdateInput 转换为 FileBulkUpdateDTO"""
        update_dto = SchemaToDTOMapper.file_update_input_to_dto(input_data.update_data)
        return FileBulkUpdateDTO(
            uids=input_data.uids,
            tenant_id=input_data.tenant_id,
            update_data=update_dto
        )
    
    @staticmethod
    def file_share_input_to_dto(input_data: FileShareInput) -> FileShareDTO:
        """FileShareInput 转换为 FileShareDTO"""
        return FileShareDTO(
            uid=input_data.uid,
            tenant_id=input_data.tenant_id,
            allowed_users=input_data.allowed_users,
            allowed_roles=input_data.allowed_roles,
            visibility=input_data.visibility
        )
    
    @staticmethod
    def file_log_create_input_to_dto(input_data: FileLogCreateInput) -> FileLogCreateDTO:
        """FileLogCreateInput 转换为 FileLogCreateDTO"""
        return FileLogCreateDTO(
            master_id=input_data.master_id,
            tenant_id=input_data.tenant_id,
            operation=input_data.operation,
            operated_by=input_data.operated_by,
            details=input_data.details,
            ip_address=input_data.ip_address,
            operation_time=input_data.operation_time or datetime.now(),
        )


class DTOToSchemaMapper:
    """DTO 到 GraphQL Schema 映射器"""
    
    @staticmethod
    def file_response_dto_to_type(dto: FileResponseDTO) -> FileType:
        """FileResponseDTO 转换为 FileType"""
        return FileType(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            filename=dto.filename,
            file_size=dto.file_size,
            content_type=dto.content_type,
            extension=dto.extension,
            file_type=dto.file_type,
            storage_bucket=dto.storage_bucket,
            storage_path=dto.storage_path,
            download_count=dto.download_count,
            proc_status=dto.proc_status,
            title=dto.title,
            desc=dto.desc,
            category=dto.category,
            tags=dto.tags,
            note=dto.note,
            status=dto.status,
            visibility=dto.visibility,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            archived_at=dto.archived_at,
            created_by=dto.created_by,
            allowed_users=dto.allowed_users,
            allowed_roles=dto.allowed_roles,
            proc_meta=dto.proc_meta,
            error_info=dto.error_info,
            metadata=dto.metadata,
        )
    
    @staticmethod
    def file_list_dto_to_type(dto: FileListDTO) -> FileListType:
        """FileListDTO 转换为 FileListType"""
        return FileListType(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            filename=dto.filename,
            file_size=dto.file_size,
            content_type=dto.content_type,
            extension=dto.extension,
            file_type=dto.file_type,
            download_count=dto.download_count,
            proc_status=dto.proc_status,
            title=dto.title,
            status=dto.status,
            visibility=dto.visibility,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
        )
    
    @staticmethod
    def file_download_dto_to_type(dto: FileDownloadDTO) -> FileDownloadType:
        """FileDownloadDTO 转换为 FileDownloadType"""
        return FileDownloadType(
            uid=dto.uid,
            filename=dto.filename,
            file_size=dto.file_size,
            content_type=dto.content_type,
            storage_bucket=dto.storage_bucket,
            storage_path=dto.storage_path,
            download_count=dto.download_count,
            title=dto.title,
            tenant_id=dto.tenant_id,
        )
    
    @staticmethod
    def file_upload_response_dto_to_type(dto: FileUploadResponseDTO) -> FileUploadResponseType:
        """FileUploadResponseDTO 转换为 FileUploadResponseType"""
        return FileUploadResponseType(
            uid=dto.uid,
            filename=dto.filename,
            file_size=dto.file_size,
            content_type=dto.content_type,
            extension=dto.extension,
            file_type=dto.file_type,
            storage_bucket=dto.storage_bucket,
            storage_path=dto.storage_path,
            title=dto.title,
            tenant_id=dto.tenant_id,
            upload_url=dto.upload_url,
            expires_in=dto.expires_in,
        )
    
    @staticmethod
    def file_statistics_dto_to_type(dto: FileStatisticsDTO) -> FileStatisticsType:
        """FileStatisticsDTO 转换为 FileStatisticsType"""
        return FileStatisticsType(
            tenant_id=dto.tenant_id,
            total_files=dto.total_files,
            total_size=dto.total_size,
            file_type_distribution=dto.file_type_distribution,
            status_distribution=dto.status_distribution,
            proc_status_distribution=dto.proc_status_distribution,
            visibility_distribution=dto.visibility_distribution,
        )
    
    @staticmethod
    def file_log_response_dto_to_type(dto: FileLogResponseDTO) -> FileLogType:
        """FileLogResponseDTO 转换为 FileLogType"""
        return FileLogType(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            operation=dto.operation,
            operated_by=dto.operated_by,
            operation_time=dto.operation_time,
            details=dto.details,
            ip_address=dto.ip_address,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            status=dto.status,
        )
    
    @staticmethod
    def file_list_dtos_to_result(
        dtos: List[FileListDTO], 
        total_count: int, 
        page: int, 
        page_size: int
    ) -> FileListResult:
        """FileListDTO 列表转换为 FileListResult"""
        items = [DTOToSchemaMapper.file_list_dto_to_type(dto) for dto in dtos]
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return FileListResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    @staticmethod
    def file_search_dtos_to_result(
        dtos: List[FileListDTO], 
        total_count: int, 
        page: int, 
        page_size: int
    ) -> FileSearchResult:
        """FileListDTO 列表转换为 FileSearchResult"""
        items = [DTOToSchemaMapper.file_list_dto_to_type(dto) for dto in dtos]
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return FileSearchResult(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    @staticmethod
    def to_operation_result(
        success: bool, 
        message: str, 
        uid: Optional[str] = None
    ) -> FileOperationResult:
        """转换为文件操作结果"""
        return FileOperationResult(
            success=success,
            message=message,
            uid=uid
        )
    
    @staticmethod
    def to_bulk_operation_result(
        success: bool,
        message: str,
        processed_count: int,
        failed_count: int,
        failed_items: List[str]
    ) -> FileBulkOperationResult:
        """转换为文件批量操作结果"""
        return FileBulkOperationResult(
            success=success,
            message=message,
            processed_count=processed_count,
            failed_count=failed_count,
            failed_items=failed_items
        )


class SchemaDTOBridge:
    """Schema 和 DTO 桥接器（统一入口）"""
    
    def __init__(self):
        self.to_dto = SchemaToDTOMapper()
        self.to_schema = DTOToSchemaMapper()
    
    # Schema -> DTO 转换方法
    def create_file_input_to_dto(self, input_data: FileCreateInput) -> FileCreateDTO:
        """转换文件创建输入"""
        return self.to_dto.file_create_input_to_dto(input_data)
    
    def update_file_input_to_dto(self, input_data: FileUpdateInput) -> FileUpdateDTO:
        """转换文件更新输入"""
        return self.to_dto.file_update_input_to_dto(input_data)
    
    def query_file_input_to_dto(self, input_data: FileQueryInput) -> FileQueryDTO:
        """转换文件查询输入"""
        return self.to_dto.file_query_input_to_dto(input_data)
    
    def search_file_input_to_dto(self, input_data: FileSearchInput) -> FileSearchDTO:
        """转换文件搜索输入"""
        return self.to_dto.file_search_input_to_dto(input_data)
    
    def bulk_update_input_to_dto(self, input_data: FileBulkUpdateInput) -> FileBulkUpdateDTO:
        """转换批量更新输入"""
        return self.to_dto.file_bulk_update_input_to_dto(input_data)
    
    def share_file_input_to_dto(self, input_data: FileShareInput) -> FileShareDTO:
        """转换文件分享输入"""
        return self.to_dto.file_share_input_to_dto(input_data)
    
    def create_log_input_to_dto(self, input_data: FileLogCreateInput) -> FileLogCreateDTO:
        """转换日志创建输入"""
        return self.to_dto.file_log_create_input_to_dto(input_data)
    
    # DTO -> Schema 转换方法
    def file_response_to_schema(self, dto: FileResponseDTO) -> FileType:
        """转换文件响应DTO"""
        return self.to_schema.file_response_dto_to_type(dto)
    
    def file_list_to_schema(self, dto: FileListDTO) -> FileListType:
        """转换文件列表DTO"""
        return self.to_schema.file_list_dto_to_type(dto)
    
    def file_download_to_schema(self, dto: FileDownloadDTO) -> FileDownloadType:
        """转换文件下载DTO"""
        return self.to_schema.file_download_dto_to_type(dto)
    
    def file_upload_to_schema(self, dto: FileUploadResponseDTO) -> FileUploadResponseType:
        """转换文件上传响应DTO"""
        return self.to_schema.file_upload_response_dto_to_type(dto)
    
    def file_statistics_to_schema(self, dto: FileStatisticsDTO) -> FileStatisticsType:
        """转换文件统计DTO"""
        return self.to_schema.file_statistics_dto_to_type(dto)
    
    def file_log_to_schema(self, dto: FileLogResponseDTO) -> FileLogType:
        """转换文件日志DTO"""
        return self.to_schema.file_log_response_dto_to_type(dto)
    
    # 批量转换方法
    def file_list_to_result(
        self, 
        dtos: List[FileListDTO], 
        total_count: int, 
        page: int, 
        page_size: int
    ) -> FileListResult:
        """转换文件列表结果为分页格式"""
        return self.to_schema.file_list_dtos_to_result(dtos, total_count, page, page_size)
    
    def file_search_to_result(
        self, 
        dtos: List[FileListDTO], 
        total_count: int, 
        page: int, 
        page_size: int
    ) -> FileSearchResult:
        """转换文件搜索结果为分页格式"""
        return self.to_schema.file_search_dtos_to_result(dtos, total_count, page, page_size)
    
    # 操作结果转换
    def operation_result(self, success: bool, message: str, uid: Optional[str] = None) -> FileOperationResult:
        """生成操作结果"""
        return self.to_schema.to_operation_result(success, message, uid)
    
    def bulk_operation_result(
        self,
        success: bool,
        message: str,
        processed_count: int,
        failed_count: int,
        failed_items: List[str]
    ) -> FileBulkOperationResult:
        """生成批量操作结果"""
        return self.to_schema.to_bulk_operation_result(
            success, message, processed_count, failed_count, failed_items
        )


# 创建全局桥接器实例
schema_dto_bridge = SchemaDTOBridge()


# 使用示例和类型别名
class FileMapper:
    """文件映射器别名（向后兼容）"""
    
    @staticmethod
    def input_to_dto(input_data: FileCreateInput) -> FileCreateDTO:
        return schema_dto_bridge.create_file_input_to_dto(input_data)
    
    @staticmethod
    def dto_to_schema(dto: FileResponseDTO) -> FileType:
        return schema_dto_bridge.file_response_to_schema(dto)
    
    @staticmethod
    def list_dtos_to_schema(dtos: List[FileListDTO], total_count: int, page: int, page_size: int) -> FileListResult:
        return schema_dto_bridge.file_list_to_result(dtos, total_count, page, page_size)


# 类型别名，便于导入
FileSchemaMapper = SchemaDTOBridge