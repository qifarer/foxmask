from typing import List, Optional
import strawberry
from strawberry.types import Info
from foxmask.file.graphql.schemas.management import (
    FileCreateInput, FileUpdateInput, FileQueryInput,
    FileType, FileListType, FileDownloadType, FileUploadResponseType,
    FileStatisticsType, FileListResult, FileSearchResult,
    FileOperationResult
)
from foxmask.file.services.management import (
    file_service, file_upload_service
)
from foxmask.file.graphql.mappers.management import FileSchemaMapper
from foxmask.core.exceptions import AuthenticationError


def get_current_user(info: Info) -> str:
    """获取当前用户"""
    return info.context.get("user_id", "SYSTEM")


def get_current_tenant(info: Info) -> str:
    """获取当前租户"""
    return info.context.get("tenant_id", "foxmask")


@strawberry.type
class FileQuery:
    """文件查询Resolver - 简化版"""
    
    @strawberry.field
    async def file(self, uid: str, info: Info) -> Optional[FileType]:
        """获取单个文件"""
        try:
            tenant_id = get_current_tenant(info)
            file_dto = await file_service.get_file(uid, tenant_id)
            return FileSchemaMapper.file_response_to_schema(file_dto) if file_dto else None
        except Exception as e:
            print(f"Error getting file: {e}")
            return None
    
    @strawberry.field
    async def files(self, query: FileQueryInput, info: Info) -> FileListResult:
        """查询文件列表"""
        try:
            tenant_id = get_current_tenant(info)
            query.tenant_id = tenant_id
            
            query_dto = FileSchemaMapper.query_file_input_to_dto(query)
            files, total_count = await file_service.list_files(query_dto)
            
            return FileSchemaMapper.file_list_to_result(
                files, total_count, query.page, query.page_size
            )
        except Exception as e:
            print(f"Error listing files: {e}")
            return FileListResult(
                items=[], total_count=0, page=query.page, 
                page_size=query.page_size, total_pages=0
            )
    
    @strawberry.field
    async def file_download(self, uid: str, info: Info) -> Optional[FileDownloadType]:
        """获取文件下载信息"""
        try:
            tenant_id = get_current_tenant(info)
            download_dto = await file_service.get_file_for_download(uid, tenant_id)
            return FileSchemaMapper.file_download_to_schema(download_dto) if download_dto else None
        except Exception as e:
            print(f"Error getting file download: {e}")
            return None
    
    @strawberry.field
    async def file_statistics(self, info: Info) -> Optional[FileStatisticsType]:
        """获取文件统计"""
        try:
            tenant_id = get_current_tenant(info)
            stats_dto = await file_service.get_file_statistics(tenant_id)
            return FileSchemaMapper.file_statistics_to_schema(stats_dto)
        except Exception as e:
            print(f"Error getting file statistics: {e}")
            return None


@strawberry.type
class FileMutation:
    """文件变更Resolver - 简化版"""
    
    @strawberry.mutation
    async def create_file(self, input_data: FileCreateInput, info: Info) -> FileUploadResponseType:
        """创建文件"""
        try:
            current_user = get_current_user(info)
            create_dto = FileSchemaMapper.create_file_input_to_dto(input_data)
            
            upload_response = await file_upload_service.prepare_upload(create_dto, current_user)
            return FileSchemaMapper.file_upload_to_schema(upload_response)
        except Exception as e:
            print(f"Error creating file: {e}")
            raise Exception("创建文件失败")
    
    @strawberry.mutation
    async def update_file(self, uid: str, input_data: FileUpdateInput, info: Info) -> FileOperationResult:
        """更新文件"""
        try:
            current_user = get_current_user(info)
            tenant_id = get_current_tenant(info)
            
            update_dto = FileSchemaMapper.update_file_input_to_dto(input_data)
            updated_file = await file_service.update_file(uid, tenant_id, update_dto, current_user)
            
            if updated_file:
                return FileOperationResult(success=True, message="文件更新成功", uid=uid)
            else:
                return FileOperationResult(success=False, message="文件不存在或更新失败", uid=uid)
        except Exception as e:
            print(f"Error updating file: {e}")
            return FileOperationResult(success=False, message=f"更新文件失败: {str(e)}", uid=uid)
    
    @strawberry.mutation
    async def delete_file(self, uid: str, info: Info) -> FileOperationResult:
        """删除文件"""
        try:
            current_user = get_current_user(info)
            tenant_id = get_current_tenant(info)
            
            success = await file_service.delete_file(uid, tenant_id, current_user)
            
            if success:
                return FileOperationResult(success=True, message="文件删除成功", uid=uid)
            else:
                return FileOperationResult(success=False, message="文件不存在或删除失败", uid=uid)
        except Exception as e:
            print(f"Error deleting file: {e}")
            return FileOperationResult(success=False, message=f"删除文件失败: {str(e)}", uid=uid)
    
    @strawberry.mutation
    async def download_file(self, uid: str, info: Info) -> FileOperationResult:
        """记录文件下载"""
        try:
            current_user = get_current_user(info)
            tenant_id = get_current_tenant(info)
            
            success = await file_service.download_file(uid, tenant_id, current_user)
            
            if success:
                return FileOperationResult(success=True, message="文件下载记录成功", uid=uid)
            else:
                return FileOperationResult(success=False, message="文件不存在或下载记录失败", uid=uid)
        except Exception as e:
            print(f"Error recording file download: {e}")
            return FileOperationResult(success=False, message=f"记录文件下载失败: {str(e)}", uid=uid)
    
    @strawberry.mutation
    async def complete_upload(self, uid: str, actual_file_size: int, info: Info) -> FileOperationResult:
        """完成文件上传"""
        try:
            current_user = get_current_user(info)
            tenant_id = get_current_tenant(info)
            
            result = await file_upload_service.complete_upload(uid, tenant_id, actual_file_size, current_user)
            
            if result:
                return FileOperationResult(success=True, message="文件上传完成", uid=uid)
            else:
                return FileOperationResult(success=False, message="文件不存在或上传完成失败", uid=uid)
        except Exception as e:
            print(f"Error completing upload: {e}")
            return FileOperationResult(success=False, message=f"完成文件上传失败: {str(e)}", uid=uid)


