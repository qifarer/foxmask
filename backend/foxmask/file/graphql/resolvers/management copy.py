# -*- coding: utf-8 -*-
# foxmask/file/resolver/file_resolver.py
import logging
from typing import List, Optional
import strawberry
from strawberry.types import Info

from foxmask.file.services import get_service_manager
from foxmask.file.graphql.schemas.management import (
    FileType, FileListType, FileStatsType,
    FileResponse, FileListResponse, FileStatsResponse,
    FileCreateInput, FileUpdateInput, FileQueryInput,
    FileUploadInput, FileUploadResponse, FileDownloadResponse
)
from foxmask.file.dtos.management import FileCreateDTO, FileUpdateDTO, FileQueryDTO

logger = logging.getLogger(__name__)

@strawberry.type
class FileMutation:
    """文件变更操作Resolver"""
    
    @strawberry.mutation
    async def create_file(
        self, 
        input: FileCreateInput, 
        info: Info
    ) -> FileResponse:
        """创建文件记录"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息（从上下文）
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 转换输入为DTO
            create_dto = FileCreateDTO(
                original_filename=input.original_filename,
                file_size=input.file_size,
                content_type=input.content_type,
                extension=input.extension,
                file_type=input.file_type,
                storage_bucket=input.storage_bucket,
                storage_key=input.storage_key,
                storage_path=input.storage_path,
                checksum_md5=input.checksum_md5,
                checksum_sha256=input.checksum_sha256,
                title=input.title,
                desc=input.desc,
                category=input.category,
                tags=input.tags or [],
                note=input.note,
                visibility=input.visibility,
                allowed_users=input.allowed_users or [],
                allowed_roles=input.allowed_roles or [],
                metadata=input.metadata or {}
            )
            
            # 调用服务层
            file_dto = await file_service.create_file(create_dto, user_id, tenant_id)
            
            # 转换为GraphQL类型
            file_type = _file_dto_to_type(file_dto)
            
            return FileResponse(
                success=True,
                message="文件创建成功",
                data=file_type,
                code=200
            )
            
        except Exception as e:
            logger.error(f"创建文件失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"文件创建失败: {str(e)}",
                data=None,
                code=500
            )
    
    @strawberry.mutation
    async def update_file(
        self, 
        file_id: str,
        input: FileUpdateInput, 
        info: Info
    ) -> FileResponse:
        """更新文件信息"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 转换输入为DTO
            update_dto = FileUpdateDTO(
                original_filename=input.filename,
                content_type=input.content_type,
                file_type=input.file_type,
                title=input.title,
                desc=input.desc,
                category=input.category,
                tags=input.tags,
                note=input.note,
                file_status=input.proc_status,
                visibility=input.visibility,
                allowed_users=input.allowed_users,
                allowed_roles=input.allowed_roles,
                metadata=input.metadata
            )
            
            # 调用服务层
            file_dto = await file_service.update_file(file_id, update_dto, user_id, tenant_id)
            
            if not file_dto:
                return FileResponse(
                    success=False,
                    message="文件不存在或无权访问",
                    data=None,
                    code=404
                )
            
            file_type = _file_dto_to_type(file_dto)
            
            return FileResponse(
                success=True,
                message="文件更新成功",
                data=file_type,
                code=200
            )
            
        except Exception as e:
            logger.error(f"更新文件失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"文件更新失败: {str(e)}",
                data=None,
                code=500
            )
    
    @strawberry.mutation
    async def delete_file(
        self, 
        file_id: str,
        info: Info
    ) -> FileResponse:
        """删除文件（软删除）"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 调用服务层
            success = await file_service.delete_file(file_id, user_id, tenant_id)
            
            if not success:
                return FileResponse(
                    success=False,
                    message="文件删除失败",
                    data=None,
                    code=404
                )
            
            return FileResponse(
                success=True,
                message="文件删除成功",
                data=None,
                code=200
            )
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"文件删除失败: {str(e)}",
                data=None,
                code=500
            )
    
    @strawberry.mutation
    async def record_file_download(
        self, 
        file_id: str,
        info: Info
    ) -> FileResponse:
        """记录文件下载"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            ip_address = context.get("ip_address")
            
            # 调用服务层
            success = await file_service.record_download(file_id, user_id, tenant_id, ip_address)
            
            if not success:
                return FileResponse(
                    success=False,
                    message="记录下载失败",
                    data=None,
                    code=404
                )
            
            return FileResponse(
                success=True,
                message="下载记录成功",
                data=None,
                code=200
            )
            
        except Exception as e:
            logger.error(f"记录文件下载失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"记录下载失败: {str(e)}",
                data=None,
                code=500
            )


@strawberry.type
class FileQuery:
    """文件查询操作Resolver"""
    
    @strawberry.field
    async def get_file(
        self, 
        file_id: str,
        info: Info
    ) -> FileResponse:
        """获取文件详情"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 调用服务层
            file_dto = await file_service.get_file(file_id, user_id, tenant_id)
            
            if not file_dto:
                return FileResponse(
                    success=False,
                    message="文件不存在或无权访问",
                    data=None,
                    code=404
                )
            
            file_type = _file_dto_to_type(file_dto)
            
            return FileResponse(
                success=True,
                message="获取文件成功",
                data=file_type,
                code=200
            )
            
        except Exception as e:
            logger.error(f"获取文件失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"获取文件失败: {str(e)}",
                data=None,
                code=500
            )
    
    @strawberry.field
    async def list_files(
        self, 
        input: FileQueryInput,
        info: Info
    ) -> FileListResponse:
        """获取文件列表"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 转换输入为DTO
            query_dto = FileQueryDTO(
                title=input.title,
                original_filename=input.original_filename,
                file_type=input.file_type,
                file_status=input.file_status,
                content_type=input.content_type,
                category=input.category,
                tags=input.tags,
                created_by=input.created_by,
                visibility=input.visibility,
                min_size=input.min_size,
                max_size=input.max_size,
                start_date=input.start_date,
                end_date=input.end_date,
                page=input.page,
                size=input.size,
                sort_by=input.sort_by,
                sort_order=input.sort_order
            )
            
            # 调用服务层
            list_dto = await file_service.list_files(query_dto, user_id, tenant_id)
            
            # 转换为GraphQL类型
            items = [_file_dto_to_type(item) for item in list_dto.items]
            list_type = FileListType(
                items=items,
                total=list_dto.total,
                page=list_dto.page,
                size=list_dto.size,
                pages=list_dto.pages
            )
            
            return FileListResponse(
                success=True,
                message="获取文件列表成功",
                data=list_type,
                code=200
            )
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return FileListResponse(
                success=False,
                message=f"获取文件列表失败: {str(e)}",
                data=None,
                code=500
            )
    
    @strawberry.field
    async def get_file_stats(
        self,
        info: Info
    ) -> FileStatsResponse:
        """获取文件统计信息"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 调用服务层
            stats_dto = await file_service.get_file_stats(tenant_id, user_id)
            
            # 转换为GraphQL类型
            stats_type = FileStatsType(
                total_files=stats_dto.total_files,
                total_size=stats_dto.total_size,
                pending_files=stats_dto.pending_files,
                processed_files=stats_dto.processed_files,
                failed_files=stats_dto.failed_files,
                by_file_type=stats_dto.by_file_type,
                by_content_type=stats_dto.by_content_type,
                daily_uploads=stats_dto.daily_uploads
            )
            
            return FileStatsResponse(
                success=True,
                message="获取文件统计成功",
                data=stats_type,
                code=200
            )
            
        except Exception as e:
            logger.error(f"获取文件统计失败: {str(e)}")
            return FileStatsResponse(
                success=False,
                message=f"获取文件统计失败: {str(e)}",
                data=None,
                code=500
            )


@strawberry.type
class FileUploadMutation:
    """文件上传相关操作Resolver"""
    
    @strawberry.mutation
    async def prepare_file_upload(
        self,
        input: FileUploadInput,
        info: Info
    ) -> FileUploadResponse:
        """准备文件上传（生成预签名URL等）"""
        try:
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            tenant_id = context.get("tenant_id", "default")
            
            # 这里可以集成MinIO/S3等存储服务生成预签名URL
            # 实际实现需要根据具体存储方案调整
            
            # 模拟实现
            file_id = f"file_{user_id}_{tenant_id}_{input.filename}"
            upload_url = f"https://storage.example.com/upload/{file_id}"
            
            return FileUploadResponse(
                success=True,
                message="上传准备成功",
                file_id=file_id,
                upload_url=upload_url,
                code=200
            )
            
        except Exception as e:
            logger.error(f"准备文件上传失败: {str(e)}")
            return FileUploadResponse(
                success=False,
                message=f"准备文件上传失败: {str(e)}",
                file_id=None,
                upload_url=None,
                code=500
            )
    
    @strawberry.mutation
    async def complete_file_upload(
        self,
        file_id: str,
        upload_success: bool,
        info: Info
    ) -> FileResponse:
        """完成文件上传（更新文件状态）"""
        try:
            service_manager = get_service_manager()
            file_service = service_manager.file_service
            
            # 获取当前用户和租户信息
            context = info.context
            user_id = context.get("user_id", "system")
            
            if upload_success:
                # 更新文件状态为已完成
                await file_service.update_file_status(
                    file_id, 
                    "completed",  # 这里应该使用具体的FileStatus枚举
                    user_id="system"
                )
                
                return FileResponse(
                    success=True,
                    message="文件上传完成",
                    data=None,
                    code=200
                )
            else:
                # 更新文件状态为失败
                await file_service.update_file_status(
                    file_id, 
                    "failed",  # 这里应该使用具体的FileStatus枚举
                    {"error": "上传过程中发生错误"},
                    user_id="system"
                )
                
                return FileResponse(
                    success=False,
                    message="文件上传失败",
                    data=None,
                    code=400
                )
            
        except Exception as e:
            logger.error(f"完成文件上传失败: {str(e)}")
            return FileResponse(
                success=False,
                message=f"完成文件上传失败: {str(e)}",
                data=None,
                code=500
            )


def _file_dto_to_type(file_dto) -> FileType:
    """将FileResponseDTO转换为FileType"""
    return FileType(
        uid=file_dto.uid,
        tenant_id=file_dto.tenant_id,
        title=file_dto.title,
        desc=file_dto.desc,
        category=file_dto.category,
        tags=file_dto.tags,
        note=file_dto.note,
        status=file_dto.status,
        visibility=file_dto.visibility,
        original_filename=file_dto.original_filename,
        file_size=file_dto.file_size,
        content_type=file_dto.content_type,
        extension=file_dto.extension,
        file_type=file_dto.file_type,
        storage_bucket=file_dto.storage_bucket,
        storage_key=file_dto.storage_key,
        storage_path=file_dto.storage_path,
        checksum_md5=file_dto.checksum_md5,
        checksum_sha256=file_dto.checksum_sha256,
        download_count=file_dto.download_count,
        file_status=file_dto.file_status,
        created_at=file_dto.created_at,
        updated_at=file_dto.updated_at,
        archived_at=file_dto.archived_at,
        created_by=file_dto.created_by,
        allowed_users=file_dto.allowed_users,
        allowed_roles=file_dto.allowed_roles,
        metadata=file_dto.metadata
    )