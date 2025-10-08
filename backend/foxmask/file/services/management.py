from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid
from foxmask.file.models.management import File, FileLog
from foxmask.file.dtos.management import *
from foxmask.file.repositories.management import *
from foxmask.file.services.management_mappers import file_mapper, file_log_mapper
from foxmask.core.enums import Status
from foxmask.file.enums import FileProcStatusEnum
from foxmask.file.repositories import get_repository_manager
from foxmask.core.logger import logger

class FileService:
    """文件服务层 - 处理文件相关的业务逻辑"""
    
    def __init__(self):
        self.file_repo = file_repository
        self.file_log_repo = file_log_repository
        self.statistics_service = file_statistics_service
        self.upload_file_repo = get_repository_manager().upload_task_file_repository
    
    async def create_file(self, create_dto: FileCreateDTO, created_by: str) -> FileResponseDTO:
        """创建文件"""
        # 生成文件UID
        file_uid = str(uuid.uuid4())
        
        # 将DTO转换为Entity
        file_entity = file_mapper.create_dto_to_entity(create_dto, file_uid, created_by)
        
        # 保存到数据库
        saved_file = await self.file_repo.create(file_entity)
        
        # 记录操作日志
        log_entity = await self._create_file_log(
            saved_file.uid, saved_file.tenant_id, "CREATE", created_by,
            details={
                "filename": create_dto.filename,
                "file_size": create_dto.file_size,
                "file_type": create_dto.file_type.value
            }
        )
        
        # 转换为响应DTO
        return file_mapper.entity_to_response_dto(saved_file)
    
    async def create_file_from_upload(self, tenant_id: str, file_id: str) -> FileResponseDTO:
        """从上传任务创建文件"""
        try:
            # 确保这里有 await
            task_file_entity = await self.upload_file_repo.get_by_id(file_id)
            
            # 检查是否找到了上传任务文件
            if not task_file_entity:
                raise ValueError(f"Upload task file not found with id: {file_id}")
            
            # 创建文件实体
            file_entity = File(
                uid=task_file_entity.uid,
                tenant_id=task_file_entity.tenant_id,
                title=task_file_entity.filename.rsplit('.', 1)[0],
                status=Status.ACTIVE,
                visibility=Visibility.PUBLIC,
                created_by="SYSTEM",
                # 文件特定字段
                filename=task_file_entity.filename,
                file_size=task_file_entity.file_size,
                content_type=task_file_entity.content_type,
                extension=task_file_entity.extension,
                file_type=task_file_entity.file_type,
                storage_bucket=task_file_entity.minio_bucket,
                storage_path=task_file_entity.minio_object_name,
                download_count=0,
                proc_status=FileProcStatusEnum.PENDING,
            )
            
            # 保存到数据库
            saved_file = await self.file_repo.create(file_entity)
            
            # 记录操作日志
            await self._create_file_log(
                saved_file.uid, saved_file.tenant_id, "CREATE", file_entity.created_by,
                details={
                    "filename": file_entity.filename,
                    "file_size": file_entity.file_size,
                    "file_type": file_entity.file_type.value
                }
            )
            
            # 转换为响应DTO
            return file_mapper.entity_to_response_dto(saved_file)
            
        except Exception as e:
            logger.error(f"Error in create_file_from_upload: {e}")
            raise
        
    
    async def get_file(self, uid: str, tenant_id: str) -> Optional[FileResponseDTO]:
        """获取文件详情"""
        file_entity = await self.file_repo.get_by_uid(uid, tenant_id)
        if not file_entity:
            return None
        
        return file_mapper.entity_to_response_dto(file_entity)
    
    async def get_file_for_download(self, uid: str, tenant_id: str) -> Optional[FileDownloadDTO]:
        """获取文件下载信息"""
        file_entity = await self.file_repo.get_by_uid(uid, tenant_id)
        if not file_entity:
            return None
        
        return file_mapper.entity_to_download_dto(file_entity)
    
    async def update_file(self, uid: str, tenant_id: str, update_dto: FileUpdateDTO, 
                        updated_by: str) -> Optional[FileResponseDTO]:
        """更新文件信息"""
        # 检查文件是否存在
        existing_file = await self.file_repo.get_by_uid(uid, tenant_id)
        if not existing_file:
            return None
        
        # 将DTO转换为更新字典
        update_data = file_mapper.update_dto_to_dict(update_dto)
        if not update_data:
            return None
        
        # 更新文件
        for field, value in update_data.items():
            if hasattr(existing_file, field):
                setattr(existing_file, field, value)
        
        existing_file.updated_at = datetime.utcnow()
        updated_file = await self.file_repo.save(existing_file)
        
        # 记录操作日志
        await self._create_file_log(
            uid, tenant_id, "UPDATE", updated_by,
            details={"updated_fields": list(update_data.keys())}
        )
        
        return file_mapper.entity_to_response_dto(updated_file)
    
    async def delete_file(self, uid: str, tenant_id: str, deleted_by: str) -> bool:
        """删除文件"""
        file_entity = await self.file_repo.get_by_uid(uid, tenant_id)
        if not file_entity:
            return False
        
        # 执行软删除
        success = await self.file_repo.soft_delete(file_entity)
        
        if success:
            # 记录操作日志
            await self._create_file_log(uid, tenant_id, "DELETE", deleted_by)
        
        return success
    
    async def list_files(self, query_dto: FileQueryDTO) -> Tuple[List[FileListDTO], int]:
        """查询文件列表"""
        # 构建查询参数
        skip = (query_dto.page - 1) * query_dto.page_size
        limit = query_dto.page_size
        
        # 使用高级搜索
        filters = {}
        if query_dto.filename:
            filters['filename'] = query_dto.filename
        if query_dto.title:
            filters['title'] = query_dto.title
        if query_dto.file_type:
            filters['file_type'] = query_dto.file_type
        if query_dto.proc_status:
            filters['proc_status'] = query_dto.proc_status
        if query_dto.content_type:
            filters['content_type'] = query_dto.content_type
        if query_dto.category:
            filters['category'] = query_dto.category
        if query_dto.tags:
            filters['tags'] = query_dto.tags
        if query_dto.status:
            filters['status'] = query_dto.status
        if query_dto.visibility:
            filters['visibility'] = query_dto.visibility
        if query_dto.created_by:
            filters['created_by'] = query_dto.created_by
        
        # 执行查询
        file_entities = await self.file_repo.advanced_search(
            query_dto.tenant_id, **filters
        )
        
        # 由于高级搜索没有内置分页，手动处理分页
        total_count = len(file_entities)
        paginated_entities = file_entities[skip:skip + limit]
        
        # 转换为DTO
        file_dtos = file_mapper.entities_to_list_dtos(paginated_entities)
        
        return file_dtos, total_count
    
    async def search_files(self, search_dto: FileSearchDTO) -> Tuple[List[FileListDTO], int]:
        """搜索文件"""
        skip = (search_dto.page - 1) * search_dto.page_size
        
        if search_dto.keyword:
            # 关键字搜索
            file_entities = await self.file_repo.search_files(
                search_dto.tenant_id, search_dto.keyword, skip, search_dto.page_size
            )
            # 搜索的总数计算需要优化，这里简化处理
            total_count = len(file_entities)
        else:
            # 精确搜索
            file_entities = await self.file_repo.advanced_search(
                search_dto.tenant_id,
                filename=search_dto.filename,
                title=search_dto.title,
                desc=search_dto.desc,
                category=search_dto.category,
                tags=search_dto.tags,
                file_type=search_dto.file_type,
                status=search_dto.status,
                visibility=search_dto.visibility,
                created_by=search_dto.created_by
            )
            total_count = len(file_entities)
            # 手动分页
            file_entities = file_entities[skip:skip + search_dto.page_size]
        
        # 转换为DTO
        file_dtos = file_mapper.entities_to_list_dtos(file_entities)
        
        return file_dtos, total_count
    
    async def download_file(self, uid: str, tenant_id: str, downloaded_by: str) -> bool:
        """记录文件下载"""
        file_entity = await self.file_repo.get_by_uid(uid, tenant_id)
        if not file_entity:
            return False
        
        # 增加下载计数
        updated_file = await self.file_repo.increment_download_count(file_entity)
        
        # 记录下载日志
        await self._create_file_log(uid, tenant_id, "DOWNLOAD", downloaded_by)
        
        return True
    
    async def update_file_status(self, uid: str, tenant_id: str, 
                               proc_status: FileProcStatusEnum,
                               proc_meta: Optional[Dict[str, Any]] = None,
                               updated_by: Optional[str] = None) -> bool:
        """更新文件处理状态"""
        file_entity = await self.file_repo.get_by_uid(uid, tenant_id)
        if not file_entity:
            return False
        
        # 更新状态
        updated_file = await self.file_repo.update_proc_status(
            file_entity, proc_status, proc_meta
        )
        
        # 记录操作日志（如果提供了操作者）
        if updated_by:
            await self._create_file_log(
                uid, tenant_id, "UPDATE_STATUS", updated_by,
                details={
                    "old_status": file_entity.proc_status.value,
                    "new_status": proc_status.value,
                    "proc_meta": proc_meta
                }
            )
        
        return True
    
    async def bulk_update_files(self, bulk_update_dto: FileBulkUpdateDTO, 
                              updated_by: str) -> Tuple[int, List[str]]:
        """批量更新文件"""
        success_count = 0
        failed_uids = []
        
        for uid in bulk_update_dto.uids:
            try:
                # 检查文件是否存在
                file_entity = await self.file_repo.get_by_uid(uid, bulk_update_dto.tenant_id)
                if not file_entity:
                    failed_uids.append(uid)
                    continue
                
                # 更新文件
                update_data = file_mapper.update_dto_to_dict(bulk_update_dto.update_data)
                for field, value in update_data.items():
                    if hasattr(file_entity, field):
                        setattr(file_entity, field, value)
                
                file_entity.updated_at = datetime.utcnow()
                await self.file_repo.save(file_entity)
                
                # 记录操作日志
                await self._create_file_log(
                    uid, bulk_update_dto.tenant_id, "BULK_UPDATE", updated_by,
                    details={"updated_fields": list(update_data.keys())}
                )
                
                success_count += 1
            except Exception:
                failed_uids.append(uid)
        
        return success_count, failed_uids
    
    async def share_file(self, share_dto: FileShareDTO, shared_by: str) -> Optional[FileResponseDTO]:
        """分享文件"""
        file_entity = await self.file_repo.get_by_uid(share_dto.uid, share_dto.tenant_id)
        if not file_entity:
            return None
        
        # 更新分享设置
        file_entity.allowed_users = share_dto.allowed_users
        file_entity.allowed_roles = share_dto.allowed_roles
        file_entity.visibility = share_dto.visibility
        file_entity.updated_at = datetime.utcnow()
        
        updated_file = await self.file_repo.save(file_entity)
        
        # 记录操作日志
        await self._create_file_log(
            share_dto.uid, share_dto.tenant_id, "SHARE", shared_by,
            details={
                "allowed_users": share_dto.allowed_users,
                "allowed_roles": share_dto.allowed_roles,
                "visibility": share_dto.visibility.value
            }
        )
        
        return file_mapper.entity_to_response_dto(updated_file)
    
    async def get_file_statistics(self, tenant_id: str) -> FileStatisticsDTO:
        """获取文件统计信息"""
        stats_data = await self.statistics_service.get_tenant_statistics(tenant_id)
        
        return FileStatisticsDTO(
            tenant_id=tenant_id,
            total_files=stats_data["total_files"],
            total_size=stats_data["total_size"],
            file_type_distribution=stats_data["file_type_distribution"],
            status_distribution=stats_data["status_distribution"],
            proc_status_distribution=stats_data["proc_status_distribution"],
            visibility_distribution=stats_data["visibility_distribution"]
        )
    
    async def get_file_logs(self, file_uid: str, tenant_id: str, 
                          page: int = 1, page_size: int = 20) -> Tuple[List[FileLogResponseDTO], int]:
        """获取文件操作日志"""
        skip = (page - 1) * page_size
        
        log_entities, total_count = await self.file_log_repo.get_by_master_id(
            file_uid, tenant_id, skip, page_size
        )
        
        # 转换为DTO
        log_dtos = file_log_mapper.entities_to_response_dtos(log_entities)
        
        return log_dtos, total_count
    
    async def find_file_by_storage_path(self, storage_bucket: str, storage_path: str) -> Optional[FileResponseDTO]:
        """根据存储路径查找文件"""
        file_entity = await self.file_repo.find_by_storage_path(storage_bucket, storage_path)
        if not file_entity:
            return None
        
        return file_mapper.entity_to_response_dto(file_entity)
    
    async def find_files_by_tags(self, tenant_id: str, tags: List[str],
                               page: int = 1, page_size: int = 20) -> Tuple[List[FileListDTO], int]:
        """根据标签查找文件"""
        skip = (page - 1) * page_size
        
        file_entities = await self.file_repo.find_by_tags(tenant_id, tags, skip, page_size)
        total_count = len(file_entities)  # 简化处理
        
        file_dtos = file_mapper.entities_to_list_dtos(file_entities)
        return file_dtos, total_count
    
    async def _create_file_log(self, master_id: str, tenant_id: str, operation: str, 
                             operated_by: str, details: Optional[Dict[str, Any]] = None) -> FileLog:
        """创建文件操作日志"""
        log_uid = str(uuid.uuid4())
        
        log_entity = FileLog(
            uid=log_uid,
            tenant_id=tenant_id,
            master_id=master_id,
            operation=operation,
            operated_by=operated_by,
            operation_time=datetime.utcnow(),
            details=details
        )
        
        return await self.file_log_repo.create(log_entity)


class FileUploadService:
    """文件上传服务"""
    
    def __init__(self, file_service: FileService):
        self.file_service = file_service
    
    async def prepare_upload(self, create_dto: FileCreateDTO, created_by: str, 
                           upload_url: Optional[str] = None, expires_in: Optional[int] = None) -> FileUploadResponseDTO:
        """准备文件上传"""
        # 创建文件记录
        file_response = await self.file_service.create_file(create_dto, created_by)
        
        # 转换为上传响应DTO
        return FileUploadResponseDTO(
            uid=file_response.uid,
            filename=file_response.filename,
            file_size=file_response.file_size,
            content_type=file_response.content_type,
            extension=file_response.extension,
            file_type=file_response.file_type,
            storage_bucket=file_response.storage_bucket,
            storage_path=file_response.storage_path,
            title=file_response.title,
            tenant_id=file_response.tenant_id,
            upload_url=upload_url,
            expires_in=expires_in
        )
    
    async def complete_upload(self, uid: str, tenant_id: str, 
                            actual_file_size: int, completed_by: str) -> Optional[FileResponseDTO]:
        """完成文件上传"""
        # 更新文件状态为已完成
        update_dto = FileUpdateDTO(
            proc_status=FileProcStatusEnum.COMPLETED,
            file_size=actual_file_size
        )
        
        return await self.file_service.update_file(uid, tenant_id, update_dto, completed_by)
    
    async def mark_upload_failed(self, uid: str, tenant_id: str, 
                               error_message: str, updated_by: str) -> bool:
        """标记上传失败"""
        update_dto = FileUpdateDTO(
            proc_status=FileProcStatusEnum.FAILED,
            error_info={"upload_error": error_message}
        )
        
        result = await self.file_service.update_file(uid, tenant_id, update_dto, updated_by)
        return result is not None


class FileQueryService:
    """文件查询服务"""
    
    def __init__(self, file_service: FileService):
        self.file_service = file_service
    
    async def query_files(self, query_dto: FileQueryDTO) -> Tuple[List[FileListDTO], int]:
        """查询文件"""
        return await self.file_service.list_files(query_dto)
    
    async def search_files(self, search_dto: FileSearchDTO) -> Tuple[List[FileListDTO], int]:
        """搜索文件"""
        return await self.file_service.search_files(search_dto)
    
    async def get_recent_files(self, tenant_id: str, limit: int = 20) -> List[FileListDTO]:
        """获取最近的文件"""
        file_entities = await file_repository.find_by_tenant(tenant_id, limit=limit)
        return file_mapper.entities_to_list_dtos(file_entities)
    
    async def get_files_by_type(self, tenant_id: str, file_type: FileTypeEnum,
                              page: int = 1, page_size: int = 20) -> Tuple[List[FileListDTO], int]:
        """根据类型获取文件"""
        skip = (page - 1) * page_size
        file_entities = await file_repository.find_by_file_type(tenant_id, file_type, skip, page_size)
        total_count = await file_repository.count_by_file_type(tenant_id, file_type)
        
        file_dtos = file_mapper.entities_to_list_dtos(file_entities)
        return file_dtos, total_count
    
    async def get_files_by_creator(self, tenant_id: str, created_by: str,
                                 page: int = 1, page_size: int = 20) -> Tuple[List[FileListDTO], int]:
        """根据创建者获取文件"""
        skip = (page - 1) * page_size
        file_entities = await file_repository.find_by_creator(tenant_id, created_by, skip, page_size)
        total_count = len(file_entities)  # 简化处理
        
        file_dtos = file_mapper.entities_to_list_dtos(file_entities)
        return file_dtos, total_count


# 创建全局服务实例
file_service = FileService()
file_upload_service = FileUploadService(file_service)
file_query_service = FileQueryService(file_service)