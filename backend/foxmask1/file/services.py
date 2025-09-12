# foxmask/file/services.py
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from minio.error import S3Error
from beanie import PydanticObjectId
from uuid import UUID
import logging
import hashlib

from foxmask.core.minio import minio_client
from foxmask.core.exceptions import NotFoundError, ServiceError, ValidationError
from foxmask.file.models import File, FileStatus, FileType, StorageProvider, FileChunk, FileVersion, FileAccessLog
from foxmask.core.tracking import tracking_service

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        from foxmask.core.minio import minio_client
        from foxmask.core.mongo import get_file_collection
        self.minio_client = minio_client
        self.get_file_collection = get_file_collection
    
    async def _check_existing_file(self, file_hash: str, user: Dict[str, Any]) -> Optional[File]:
        """
        检查文件是否已存在（基于文件哈希）
        """
        try:
            # 使用 Beanie 2.0.0 查询语法
            existing_files = await File.find(
                File.metadata.hash == file_hash,
                File.is_deleted == False,
                File.owner_id == user.get("id")
            ).to_list()
            
            return existing_files[0] if existing_files else None
            
        except Exception as e:
            logger.error(f"Failed to check existing file: {e}")
            return None
    
    def _determine_file_type(self, filename: str) -> FileType:
        """
        根据文件名确定文件类型（同步方法）
        """
        if not filename:
            return FileType.OTHER
        
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # 图片类型
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff', 'ico']
        if extension in image_extensions:
            return FileType.IMAGE
        
        # 文档类型
        document_extensions = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages', 'md', 'ppt', 'pptx']
        if extension in document_extensions:
            return FileType.DOCUMENT
        
        # 视频类型
        video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', 'm4v', '3gp']
        if extension in video_extensions:
            return FileType.VIDEO
        
        # 音频类型
        audio_extensions = ['mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma', 'amr']
        if extension in audio_extensions:
            return FileType.AUDIO
        
        # 压缩文件
        archive_extensions = ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso']
        if extension in archive_extensions:
            return FileType.ARCHIVE
        
        # 代码文件
        code_extensions = ['py', 'js', 'java', 'cpp', 'c', 'html', 'css', 'php', 'rb', 'go', 'ts', 'json', 'xml', 'yaml', 'yml']
        if extension in code_extensions:
            return FileType.CODE
        
        # 数据文件
        data_extensions = ['csv', 'xlsx', 'xls', 'db', 'sqlite', 'dat']
        if extension in data_extensions:
            return FileType.DATA
        
        return FileType.OTHER
    
    async def _upload_to_storage(self, bucket_name: str, object_key: str, content: bytes):
        """
        上传文件到存储系统
        """
        try:
            # 确保存储桶存在
            if not self.minio_client.bucket_exists(bucket_name):
                self.minio_client.make_bucket(bucket_name)
            
            # 上传文件
            self.minio_client.put_object(
                bucket_name,
                object_key,
                content,
                len(content)
            )
            
            logger.info(f"File uploaded to storage: {bucket_name}/{object_key}")
            
        except S3Error as e:
            logger.error(f"Failed to upload to storage: {e}")
            raise ServiceError(f"Failed to upload file to storage: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during storage upload: {e}")
            raise ServiceError(f"Failed to upload file: {e}")

    async def create_file(self, filename: str, size: int, content_type: str, 
                         owner_id: str, bucket_name: str, object_key: str,
                         file_type: FileType,
                         user: Dict[str, Any] = None, 
                         tenant_id: Optional[str] = None, project_id: Optional[str] = None,
                         tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None,
                         is_public: bool = False) -> File:
        """
        创建文件记录
        """
        try:
            # 提取文件扩展名
            extension = self._extract_extension(filename)
            
            # 直接创建 File 实例
            file = File(
                filename=filename,
                original_filename=filename,
                size=size,
                content_type=content_type,
                extension=extension,
                file_type=file_type,
                bucket_name=bucket_name,
                object_key=object_key,
                owner_id=owner_id,
                tenant_id=tenant_id or (user.get("tenant_id") if user else None),
                project_id=project_id,
                tags=tags or [],
                metadata=metadata or {},
                is_public=is_public,
                created_by=user.get("id") if user else None,
                updated_by=user.get("id") if user else None
            )
            
            await file.insert()
            
            # 记录文件创建事件
            if user:
                await tracking_service.log_file_operation(
                    operation="file_create",
                    file_id=str(file.id),
                    filename=filename,
                    user=user,
                    details={
                        "size": size,
                        "content_type": content_type,
                        "file_type": file_type.value
                    }
                )
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to create file: {e}", exc_info=True)
            raise ServiceError(f"Failed to create file: {e}")
            
    async def get_file(self, file_id: str, user: Dict[str, Any]) -> Optional[File]:
        """
        获取文件信息
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                return None
            
            # 检查访问权限
            if not self._check_file_access(file, user):
                raise ServiceError("Access denied")
            
            # 更新访问时间
            file.accessed_at = datetime.now(timezone.utc)
            await file.save()
            
            # 记录访问日志
            await self._log_file_access(file, user, "view")
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to get file {file_id}: {e}")
            raise ServiceError(f"Failed to get file: {e}")
    
    async def update_file(self, file_id: str, user: Dict[str, Any],
                         updates: Dict[str, Any]) -> Optional[File]:
        """
        更新文件信息
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                raise NotFoundError("File not found")
            
            # 检查权限（只有所有者可以更新）
            if file.owner_id != user.get("id"):
                raise ServiceError("Access denied")
            
            # 应用更新
            for key, value in updates.items():
                if hasattr(file, key) and value is not None:
                    setattr(file, key, value)
            
            file.updated_by = user.get("id")
            file.uploaded_at = datetime.now(timezone.utc)  # 手动更新时间戳
            await file.save()
            
            # 记录更新事件
            await tracking_service.log_file_operation(
                operation="file_update",
                file_id=file_id,
                filename=file.filename,
                user=user,
                details={"updates": updates}
            )
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to update file {file_id}: {e}")
            raise ServiceError(f"Failed to update file: {e}")
    
    async def list_files(self, user: Dict[str, Any], skip: int = 0, limit: int = 100,
                        filters: Optional[Dict[str, Any]] = None) -> List[File]:
        """
        列出文件（支持过滤）
        """
        try:
            # 基础查询
            query = File.find(File.is_deleted == False)
            
            # 添加用户特定的过滤条件
            user_roles = user.get("roles", [])
            is_admin = any(role in user_roles for role in ["admin", "administrator", "superadmin"])
            
            if not is_admin:
                query = query.find(
                    (File.owner_id == user.get("id")) |
                    (File.is_public == True) |
                    ((File.tenant_id == user.get("tenant_id")) & (File.access_control.users == user.get("id")))
                )
            
            # 添加自定义过滤条件
            if filters:
                for key, value in filters.items():
                    if hasattr(File, key):
                        query = query.find(getattr(File, key) == value)
            
            files = await query.skip(skip).limit(limit).to_list()
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise ServiceError(f"Failed to list files: {e}")
    
    async def delete_file(self, file_id: str, user: Dict[str, Any]) -> bool:
        """
        删除文件（软删除）
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                raise NotFoundError("File not found")
            
            # 检查权限（只有所有者可以删除）
            user_roles = user.get("roles", [])
            is_admin = any(role in user_roles for role in ["admin", "administrator", "superadmin"])
            
            if file.owner_id != user.get("id") and not is_admin:
                raise ServiceError("Access denied")
            
            # 软删除
            file.is_deleted = True
            file.deleted_at = datetime.now(timezone.utc)
            file.status = FileStatus.DELETED
            await file.save()
            
            # 记录删除事件
            await tracking_service.log_file_operation(
                operation="file_delete",
                file_id=file_id,
                filename=file.filename,
                user=user,
                details={
                    "size": file.size,
                    "content_type": file.content_type
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            raise ServiceError(f"Failed to delete file: {e}")
    
    async def get_presigned_url(self, file_id: str, user: Dict[str, Any],
                               expires: int = 3600) -> str:
        """
        获取预签名URL
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                raise NotFoundError("File not found")
            
            # 检查访问权限
            if not self._check_file_access(file, user):
                raise ServiceError("Access denied")
            
            # 生成预签名URL
            url = self.minio_client.presigned_get_object(
                file.bucket_name,
                file.object_key,
                expires=expires
            )
            
            # 更新访问时间
            file.accessed_at = datetime.now(timezone.utc)
            await file.save()
            
            # 记录访问日志
            await self._log_file_access(file, user, "download")
            
            # 记录下载事件
            await tracking_service.log_file_operation(
                operation="file_download",
                file_id=file_id,
                filename=file.filename,
                user=user,
                details={"expires": expires}
            )
            
            return url
            
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for file {file_id}: {e}")
            raise ServiceError(f"Failed to generate download URL: {e}")
        except Exception as e:
            logger.error(f"Failed to get presigned URL for file {file_id}: {e}")
            raise ServiceError(f"Failed to get download URL: {e}")
    
    async def upload_file_chunk(self, file_id: str, chunk_number: int, 
                               chunk_data: bytes, user: Dict[str, Any]) -> bool:
        """
        上传文件分块
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                raise NotFoundError("File not found")
            
            # 检查权限
            if file.owner_id != user.get("id"):
                raise ServiceError("Access denied")
            
            # 创建分块记录
            chunk = FileChunk(
                file_id=file.id,
                chunk_number=chunk_number,
                chunk_size=len(chunk_data),
                total_chunks=0,  # 需要在complete_upload时更新
                storage_provider=file.storage_provider,
                bucket_name=file.bucket_name,
                object_key=f"{file.object_key}_chunk_{chunk_number}",
                checksum=self._calculate_checksum(chunk_data)
            )
            
            await chunk.insert()
            
            # 上传分块到存储
            self.minio_client.put_object(
                chunk.bucket_name,
                chunk.object_key,
                chunk_data,
                len(chunk_data)
            )
            
            # 更新分块状态
            chunk.is_uploaded = True
            chunk.uploaded_at = datetime.now(timezone.utc)
            await chunk.save()
            
            # 记录分块上传事件
            await tracking_service.log_file_operation(
                operation="chunk_upload",
                file_id=file_id,
                filename=file.filename,
                user=user,
                details={
                    "chunk_number": chunk_number,
                    "chunk_size": len(chunk_data)
                }
            )
            
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload chunk for file {file_id}: {e}")
            raise ServiceError(f"Failed to upload file chunk: {e}")
        except Exception as e:
            logger.error(f"Failed to upload chunk for file {file_id}: {e}")
            raise ServiceError(f"Failed to upload file chunk: {e}")
    
    async def complete_file_upload(self, file_id: str, user: Dict[str, Any]) -> File:
        """
        完成文件上传
        """
        try:
            if not PydanticObjectId.is_valid(file_id):
                raise ValidationError("Invalid file ID format")
            
            file = await File.get(PydanticObjectId(file_id))
            if not file:
                raise NotFoundError("File not found")
            
            # 检查权限
            if file.owner_id != user.get("id"):
                raise ServiceError("Access denied")
            
            # 合并分块
            await self._combine_chunks(file)
            
            # 更新文件状态
            file.status = FileStatus.PROCESSED
            file.processed_at = datetime.now(timezone.utc)
            file.processed_by = user.get("id")
            await file.save()
            
            # 记录上传完成事件
            await tracking_service.log_file_operation(
                operation="upload_complete",
                file_id=file_id,
                filename=file.filename,
                user=user,
                details={
                    "size": file.size,
                    "status": file.status.value
                }
            )
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to complete upload for file {file_id}: {e}")
            raise ServiceError(f"Failed to complete file upload: {e}")
    
    async def search_files(self, query: str, user: Dict[str, Any],
                      skip: int = 0, limit: int = 100) -> List[File]:
        """
        搜索文件（使用正则表达式作为后备方案）
        """
        try:
            # 首先尝试文本搜索
            try:
                from beanie.operators import Text
                search_query = File.find(
                    Text(query),
                    File.is_deleted == False
                )
            except Exception:
                # 如果文本搜索不可用，使用正则表达式作为后备
                logger.warning("Text search not available, using regex fallback")
                search_query = File.find(
                    File.filename.regex(query, "i"),  # 不区分大小写
                    File.is_deleted == False
                )
            
            # 添加权限过滤
            user_roles = user.get("roles", [])
            is_admin = any(role in user_roles for role in ["admin", "administrator", "superadmin"])
            
            if not is_admin:
                search_query = search_query.find(
                    (File.owner_id == user.get("id")) |
                    (File.is_public == True) |
                    ((File.tenant_id == user.get("tenant_id")) & (File.access_control.users == user.get("id")))
                )
            
            files = await search_query.skip(skip).limit(limit).to_list()
            return files
            
        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            raise ServiceError(f"Failed to search files: {e}")
    
    
    # 辅助方法
    def _extract_extension(self, filename: str) -> str:
        """提取文件扩展名"""
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        return ''
    
    def _calculate_checksum(self, data: bytes) -> str:
        """计算数据校验和"""
        return hashlib.md5(data).hexdigest()
    
    def _check_file_access(self, file: File, user: Dict[str, Any]) -> bool:
        """检查文件访问权限"""
        # 管理员有完全访问权限
        user_roles = user.get("roles", [])
        is_admin = any(role in user_roles for role in ["admin", "administrator", "superadmin"])
        
        if is_admin:
            return True
        
        # 公开文件任何人都可以访问
        if file.is_public:
            return True
        
        # 所有者可以访问自己的文件
        if file.owner_id == user.get("id"):
            return True
        
        # 同一租户的用户可以访问租户文件
        user_tenant = user.get("tenant_id") or user.get("casdoor_org")
        if file.tenant_id and file.tenant_id == user_tenant:
            return True
        
        # 检查访问控制列表
        if user.get("id") in file.access_control.get("users", []):
            return True
        
        return False
    
    async def _log_file_access(self, file: File, user: Dict[str, Any], action: str):
        """记录文件访问日志"""
        access_log = FileAccessLog(
            file_id=file.id,
            user_id=user.get("id"),
            action=action,
            ip_address=user.get("ip_address"),
            user_agent=user.get("user_agent"),
            success=True
        )
        await access_log.insert()
    
    async def _combine_chunks(self, file: File):
        """合并文件分块（MinIO 实现）"""
        try:
            # 获取所有分块
            chunks = await FileChunk.find(
                FileChunk.file_id == file.id,
                FileChunk.is_uploaded == True
            ).to_list()
            
            if not chunks:
                raise ServiceError("No chunks found to combine")
            
            # MinIO 分块合并逻辑
            sources = []
            for chunk in chunks:
                sources.append({
                    'bucket_name': chunk.bucket_name,
                    'object_name': chunk.object_key
                })
            
            # 使用 MinIO 的 compose_object API 合并分块
            self.minio_client.compose_object(
                file.bucket_name,
                file.object_key,
                sources
            )
            
            logger.info(f"Successfully combined {len(chunks)} chunks for file {file.id}")
            
        except S3Error as e:
            logger.error(f"Failed to combine chunks for file {file.id}: {e}")
            raise ServiceError(f"Failed to combine file chunks: {e}")
        except Exception as e:
            logger.error(f"Unexpected error combining chunks: {e}")
            raise ServiceError(f"Failed to combine chunks: {e}")

# 全局文件服务实例
file_service = FileService()