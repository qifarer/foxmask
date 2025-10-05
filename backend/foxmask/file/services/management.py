# -*- coding: utf-8 -*-
# foxmask/file/service/file_service.py
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import uuid4

from foxmask.file.repositories import get_repository_manager
from foxmask.file.dtos.management import (
    FileCreateDTO, FileUpdateDTO, FileResponseDTO, FileQueryDTO, 
    FileListDTO, FileStatsDTO, FileLogCreateDTO, FileLogResponseDTO
)
from foxmask.file.models.management import File, FileLog
from foxmask.file.enums import FileTypeEnum, UploadProcStatusEnum
from foxmask.core.model import Status, Visibility


logger = logging.getLogger(__name__)

class FileService:
    """文件管理服务"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
        self.file_repo = self.repo_manager.file_repository
        self.file_log_repo = self.repo_manager.file_log_repository
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def create_file(self, create_dto: FileCreateDTO, user_id: str, tenant_id: str) -> FileResponseDTO:
        """创建文件记录"""
        try:
            # 生成唯一ID
            file_uid = f"file_{uuid4().hex[:16]}"
            
            # 构建文件数据
            file_data = {
                "uid": file_uid,
                "tenant_id": tenant_id,
                "title": create_dto.title or create_dto.original_filename,
                "desc": create_dto.desc,
                "category": create_dto.category,
                "tags": create_dto.tags,
                "note": create_dto.note,
                "status": Status.ACTIVE,
                "visibility": create_dto.visibility,
                "created_by": user_id,
                "allowed_users": create_dto.allowed_users,
                "allowed_roles": create_dto.allowed_roles,
                "metadata": create_dto.metadata,
                
                # 文件特定字段
                "original_filename": create_dto.original_filename,
                "file_size": create_dto.file_size,
                "content_type": create_dto.content_type,
                "extension": create_dto.extension,
                "file_type": create_dto.file_type,
                "storage_bucket": create_dto.storage_bucket,
                "storage_key": create_dto.storage_key,
                "storage_path": create_dto.storage_path,
                "checksum_md5": create_dto.checksum_md5,
                "checksum_sha256": create_dto.checksum_sha256,
                "file_status": UploadProcStatusEnum.PENDING
            }
            
            # 创建文件记录
            file = await self.file_repo.create_file(file_data)
            
            # 记录创建日志
            await self.file_log_repo.create_log({
                "uid": f"log_{uuid4().hex[:16]}",
                "tenant_id": tenant_id,
                "master_id": file.id,
                "operation": "CREATE",
                "operated_by": user_id,
                "details": {
                    "filename": create_dto.original_filename,
                    "size": create_dto.file_size,
                    "file_type": create_dto.file_type.value
                }
            })
            
            self.logger.info(f"File created successfully: {file_uid} by user {user_id}")
            return self._file_to_response_dto(file)
            
        except Exception as e:
            self.logger.error(f"Failed to create file: {str(e)}")
            raise
    
    async def get_file(self, file_id: str, user_id: str, tenant_id: str) -> Optional[FileResponseDTO]:
        """获取文件详情"""
        try:
            file = await self.file_repo.get_by_id(file_id)
            
            if not file:
                return None
            
            # 验证租户访问权限
            if file.tenant_id != tenant_id:
                self.logger.warning(f"User {user_id} from tenant {tenant_id} tried to access file from tenant {file.tenant_id}")
                return None
            
            # 验证用户访问权限
            if not self._check_file_access(file, user_id):
                self.logger.warning(f"User {user_id} does not have access to file {file_id}")
                return None
            
            return self._file_to_response_dto(file)
            
        except Exception as e:
            self.logger.error(f"Failed to get file {file_id}: {str(e)}")
            raise
    
    async def update_file(self, file_id: str, update_dto: FileUpdateDTO, user_id: str, tenant_id: str) -> Optional[FileResponseDTO]:
        """更新文件信息"""
        try:
            # 检查文件是否存在和权限
            file = await self.file_repo.get_by_id(file_id)
            if not file or file.tenant_id != tenant_id:
                return None
            
            # 构建更新数据
            update_data = {}
            if update_dto.original_filename is not None:
                update_data["original_filename"] = update_dto.original_filename
            if update_dto.content_type is not None:
                update_data["content_type"] = update_dto.content_type
            if update_dto.file_type is not None:
                update_data["file_type"] = update_dto.file_type
            if update_dto.title is not None:
                update_data["title"] = update_dto.title
            if update_dto.desc is not None:
                update_data["desc"] = update_dto.desc
            if update_dto.category is not None:
                update_data["category"] = update_dto.category
            if update_dto.tags is not None:
                update_data["tags"] = update_dto.tags
            if update_dto.note is not None:
                update_data["note"] = update_dto.note
            if update_dto.file_status is not None:
                update_data["file_status"] = update_dto.file_status
            if update_dto.visibility is not None:
                update_data["visibility"] = update_dto.visibility
            if update_dto.allowed_users is not None:
                update_data["allowed_users"] = update_dto.allowed_users
            if update_dto.allowed_roles is not None:
                update_data["allowed_roles"] = update_dto.allowed_roles
            if update_dto.metadata is not None:
                update_data["metadata"] = update_dto.metadata
            
            if update_data:
                updated_file = await self.file_repo.update_file(file_id, update_data)
                
                # 记录更新日志
                await self.file_log_repo.create_log({
                    "uid": f"log_{uuid4().hex[:16]}",
                    "tenant_id": tenant_id,
                    "master_id": file_id,
                    "operation": "UPDATE",
                    "operated_by": user_id,
                    "details": {
                        "updated_fields": list(update_data.keys())
                    }
                })
                
                self.logger.info(f"File updated successfully: {file_id} by user {user_id}")
                return self._file_to_response_dto(updated_file)
            
            return self._file_to_response_dto(file)
            
        except Exception as e:
            self.logger.error(f"Failed to update file {file_id}: {str(e)}")
            raise
    
    async def delete_file(self, file_id: str, user_id: str, tenant_id: str) -> bool:
        """删除文件（软删除）"""
        try:
            file = await self.file_repo.get_by_id(file_id)
            if not file or file.tenant_id != tenant_id:
                return False
            
            # 执行软删除
            update_data = {
                "status": Status.ARCHIVED,
                "file_status": UploadProcStatusEnum.DELETED
            }
            
            await self.file_repo.update_file(file_id, update_data)
            
            # 记录删除日志
            await self.file_log_repo.create_log({
                "uid": f"log_{uuid4().hex[:16]}",
                "tenant_id": tenant_id,
                "master_id": file_id,
                "operation": "DELETE",
                "operated_by": user_id,
                "details": {
                    "filename": file.original_filename,
                    "soft_delete": True
                }
            })
            
            self.logger.info(f"File deleted successfully: {file_id} by user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_id}: {str(e)}")
            raise
    
    async def list_files(self, query_dto: FileQueryDTO, user_id: str, tenant_id: str) -> FileListDTO:
        """获取文件列表"""
        try:
            # 构建查询过滤器
            filters = self._build_query_filters(query_dto)
            
            # 计算分页
            skip = (query_dto.page - 1) * query_dto.size
            
            # 查询文件
            files, total = await self.file_repo.list_files(
                tenant_id=tenant_id,
                skip=skip,
                limit=query_dto.size,
                sort_field=query_dto.sort_by,
                sort_order=query_dto.sort_order,
                **filters
            )
            
            # 过滤有访问权限的文件
            accessible_files = [
                file for file in files 
                if self._check_file_access(file, user_id)
            ]
            
            # 计算总页数
            pages = (total + query_dto.size - 1) // query_dto.size
            
            return FileListDTO(
                items=[self._file_to_response_dto(file) for file in accessible_files],
                total=len(accessible_files),  # 返回实际可访问的数量
                page=query_dto.page,
                size=query_dto.size,
                pages=pages
            )
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}")
            raise
    
    async def record_download(self, file_id: str, user_id: str, tenant_id: str, ip_address: str = None) -> bool:
        """记录文件下载"""
        try:
            file = await self.file_repo.get_by_id(file_id)
            if not file or file.tenant_id != tenant_id:
                return False
            
            # 增加下载计数
            await self.file_repo.increment_download_count(file_id)
            
            # 记录下载日志
            await self.file_log_repo.create_log({
                "uid": f"log_{uuid4().hex[:16]}",
                "tenant_id": tenant_id,
                "master_id": file_id,
                "operation": "DOWNLOAD",
                "operated_by": user_id,
                "ip_address": ip_address,
                "details": {
                    "filename": file.original_filename,
                    "size": file.file_size
                }
            })
            
            self.logger.info(f"File download recorded: {file_id} by user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record download for file {file_id}: {str(e)}")
            raise
    
    async def update_file_status(self, file_id: str, status: UploadProcStatusEnum, error_info: Dict[str, Any] = None, 
                               user_id: str = "system") -> bool:
        """更新文件处理状态"""
        try:
            file = await self.file_repo.get_by_id(file_id)
            if not file:
                return False
            
            await self.file_repo.update_file_status(file_id, status, error_info)
            
            # 记录状态变更日志
            await self.file_log_repo.create_log({
                "uid": f"log_{uuid4().hex[:16]}",
                "tenant_id": file.tenant_id,
                "master_id": file_id,
                "operation": "STATUS_UPDATE",
                "operated_by": user_id,
                "details": {
                    "new_status": status.value,
                    "error_info": error_info
                }
            })
            
            self.logger.info(f"File status updated: {file_id} to {status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update file status for {file_id}: {str(e)}")
            raise
    
    async def get_file_stats(self, tenant_id: str, user_id: str) -> FileStatsDTO:
        """获取文件统计信息"""
        try:
            stats = await self.file_repo.get_file_stats(tenant_id)
            
            return FileStatsDTO(
                total_files=stats["total_files"],
                total_size=stats["total_size"],
                pending_files=stats["by_status"].get(UploadProcStatusEnum.PENDING, 0),
                processed_files=stats["by_status"].get(UploadProcStatusEnum.COMPLETED, 0),
                failed_files=stats["by_status"].get(UploadProcStatusEnum.FAILED, 0),
                by_file_type=stats["by_file_type"],
                by_content_type={},  # 需要额外实现
                daily_uploads={}     # 需要额外实现
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get file stats for tenant {tenant_id}: {str(e)}")
            raise
    
    def _check_file_access(self, file: File, user_id: str) -> bool:
        """检查文件访问权限"""
        # 公开文件所有人都可以访问
        if file.visibility == Visibility.PUBLIC:
            return True
        
        # 租户内文件，租户内用户都可以访问
        # 这里假设同一个租户内的用户都可以访问（实际可能需要更复杂的权限检查）
        if file.visibility == Visibility.TENANT:
            return True
        
        # 私有文件，只允许特定用户访问
        if file.visibility == Visibility.PRIVATE:
            return user_id in file.allowed_users or user_id == file.created_by
        
        return False
    
    def _build_query_filters(self, query_dto: FileQueryDTO) -> Dict[str, Any]:
        """构建查询过滤器"""
        filters = {}
        
        if query_dto.title:
            filters["title"] = query_dto.title
        if query_dto.original_filename:
            filters["original_filename"] = query_dto.original_filename
        if query_dto.file_type:
            filters["file_type"] = query_dto.file_type
        if query_dto.file_status:
            filters["file_status"] = query_dto.file_status
        if query_dto.content_type:
            filters["content_type"] = query_dto.content_type
        if query_dto.category:
            filters["category"] = query_dto.category
        if query_dto.tags:
            filters["tags"] = query_dto.tags
        if query_dto.created_by:
            filters["created_by"] = query_dto.created_by
        if query_dto.visibility:
            filters["visibility"] = query_dto.visibility
        if query_dto.min_size is not None:
            filters["min_size"] = query_dto.min_size
        if query_dto.max_size is not None:
            filters["max_size"] = query_dto.max_size
        if query_dto.start_date:
            filters["start_date"] = query_dto.start_date
        if query_dto.end_date:
            filters["end_date"] = query_dto.end_date
        
        return filters
    
    def _file_to_response_dto(self, file: File) -> FileResponseDTO:
        """将File模型转换为FileResponseDTO"""
        return FileResponseDTO(
            uid=file.uid,
            tenant_id=file.tenant_id,
            title=file.title,
            desc=file.desc,
            category=file.category,
            tags=file.tags,
            note=file.note,
            status=file.status,
            visibility=file.visibility,
            original_filename=file.original_filename,
            file_size=file.file_size,
            content_type=file.content_type,
            extension=file.extension,
            file_type=file.file_type,
            storage_bucket=file.storage_bucket,
            storage_key=file.storage_key,
            storage_path=file.storage_path,
            checksum_md5=file.checksum_md5,
            checksum_sha256=file.checksum_sha256,
            download_count=file.download_count,
            file_status=file.file_status,
            created_at=file.created_at,
            updated_at=file.updated_at,
            archived_at=file.archived_at,
            created_by=file.created_by,
            allowed_users=file.allowed_users,
            allowed_roles=file.allowed_roles,
            metadata=file.metadata
        )


class FileLogService:
    """文件日志服务"""
    
    def __init__(self):
        self.repo_manager = get_repository_manager()
        self.file_log_repo = self.repo_manager.file_log_repository
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_file_logs(self, file_id: str, user_id: str, tenant_id: str, limit: int = 100) -> List[FileLogResponseDTO]:
        """获取文件操作日志"""
        try:
            logs = await self.file_log_repo.get_logs_by_file(file_id, limit)
            
            # 过滤当前用户有权限查看的日志
            accessible_logs = [
                log for log in logs 
                if log.tenant_id == tenant_id  # 只能查看本租户的日志
            ]
            
            return [self._log_to_response_dto(log) for log in accessible_logs]
            
        except Exception as e:
            self.logger.error(f"Failed to get logs for file {file_id}: {str(e)}")
            raise
    
    async def get_user_operation_stats(self, user_id: str, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户操作统计"""
        try:
            stats = await self.file_log_repo.get_operation_stats(tenant_id, days)
            
            # 过滤当前用户的数据
            user_stats = {
                "total_operations": stats["by_user"].get(user_id, 0),
                "operations_by_type": {
                    op_type: count 
                    for op_type, count in stats["by_operation_type"].items()
                }
            }
            
            return user_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get operation stats for user {user_id}: {str(e)}")
            raise
    
    def _log_to_response_dto(self, log: FileLog) -> FileLogResponseDTO:
        """将FileLog模型转换为FileLogResponseDTO"""
        return FileLogResponseDTO(
            uid=log.uid,
            tenant_id=log.tenant_id,
            master_id=log.master_id,
            operation=log.operation,
            operated_by=log.operated_by,
            operation_time=log.operation_time,
            details=log.details,
            ip_address=log.ip_address,
            note=log.note,
            created_at=log.created_at,
            updated_at=log.updated_at
        )