# foxmask/file/services/file_service.py
import math
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from foxmask.core.config import settings
from foxmask.core.exceptions import (
    FileProcessingError, NotFoundError, ValidationError, ExternalServiceError
)
from foxmask.core.logger import logger
from foxmask.file.models import (
    FileMetadata, FileChunk, FileStatus, FileVisibility, FileType, ChunkStatus
)
from foxmask.file.dtos import (
    FileCreateDTO, FileUpdateDTO, FileResponseDTO, 
    ChunkUploadDTO, UploadProgressDTO
)
from foxmask.file.repositories import RepositoryManager
from foxmask.utils.helpers import get_current_time, calculate_md5_hash, generate_uuid

class FileService:
    """文件服务"""
    
    def __init__(self, repository_manager: RepositoryManager):
        self.repo = repository_manager
        self.chunk_size = settings.CHUNK_SIZE or 5 * 1024 * 1024  # 5MB
    
    def _determine_file_type(self, filename: str, content_type: str) -> FileType:
        """根据文件名和内容类型确定文件类型"""
        # 简化的文件类型检测逻辑
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'flv']
        audio_extensions = ['mp3', 'wav', 'flac', 'aac']
        archive_extensions = ['zip', 'rar', '7z', 'tar', 'gz']
        document_extensions = ['pdf', 'doc', 'docx', 'txt', 'rtf']
        
        if extension in image_extensions or content_type.startswith('image/'):
            return FileType.IMAGE
        elif extension in video_extensions or content_type.startswith('video/'):
            return FileType.VIDEO
        elif extension in audio_extensions or content_type.startswith('audio/'):
            return FileType.AUDIO
        elif extension in archive_extensions or 'zip' in content_type:
            return FileType.ARCHIVE
        elif extension in document_extensions or 'pdf' in content_type:
            return FileType.DOCUMENT
        else:
            return FileType.OTHER
    
    async def create_file(self, file_data: FileCreateDTO, user_id: str, tenant_id: str) -> FileMetadata:
        """创建文件记录"""
        try:
            # 确定文件类型
            file_type = self._determine_file_type(file_data.filename, file_data.content_type)
            extension = file_data.filename.split('.')[-1] if '.' in file_data.filename else ''
            
            # 生成存储路径
            minio_object_name = f"{tenant_id}/{user_id}/{generate_uuid()}/{file_data.filename}"
            minio_bucket = f"tenant-{tenant_id}"
            
            file_dict = {
                "filename": file_data.filename,
                "original_filename": file_data.filename,
                "file_size": file_data.file_size,
                "content_type": file_data.content_type,
                "extension": extension,
                "file_type": file_type,
                "minio_bucket": minio_bucket,
                "minio_object_name": minio_object_name,
                "storage_path": minio_object_name,
                "uploaded_by": user_id,
                "tenant_id": tenant_id,
                "status": FileStatus.DRAFT,
                "is_multipart": file_data.is_multipart,
                "chunk_size": file_data.chunk_size,
                "description": file_data.description,
                "tags": file_data.tags,
                "remark": file_data.remark,
                "visibility": file_data.visibility,
                "allowed_users": file_data.allowed_users,
                "allowed_roles": file_data.allowed_roles,
                "metadata": file_data.metadata
            }
            
            return await self.repo.file_repo.create_file(file_dict)
            
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            raise FileProcessingError("create_file", str(e))
    
    async def init_multipart_upload(self, file_data: Dict[str, Any], user_id: str, tenant_id: str) -> Dict[str, Any]:
        """初始化分块上传"""
        try:
            # 创建文件DTO
            file_dto = FileCreateDTO(**file_data)
            file = await self.create_file(file_dto, user_id, tenant_id)
            
            # 计算分块信息
            total_chunks = math.ceil(file.file_size / file.chunk_size)
            
            # 生成上传ID（这里简化处理，实际应该调用MinIO API）
            upload_id = generate_uuid()
            
            # 更新文件记录
            await self.repo.file_repo.update_file(file.id, {
                "upload_id": upload_id,
                "status": FileStatus.UPLOADING,
                "total_chunks": total_chunks
            })
            
            # 创建分块记录
            chunks = []
            for chunk_number in range(1, total_chunks + 1):
                start_byte = (chunk_number - 1) * file.chunk_size
                end_byte = min(start_byte + file.chunk_size, file.file_size) - 1
                
                chunk = FileChunk(
                    file_id=file.id,
                    upload_id=upload_id,
                    chunk_number=chunk_number,
                    chunk_size=file.chunk_size,
                    start_byte=start_byte,
                    end_byte=end_byte,
                    minio_bucket=file.minio_bucket,
                    minio_object_name=f"{file.minio_object_name}.part{chunk_number}",
                    status=ChunkStatus.PENDING
                )
                chunks.append(chunk)
            
            await self.repo.chunk_repo.create_chunks(chunks)
            
            # 生成分块上传URL（简化版，实际需要调用MinIO生成预签名URL）
            chunk_urls = {}
            for chunk_number in range(1, total_chunks + 1):
                # 这里应该是调用MinIO生成预签名URL的逻辑
                chunk_urls[chunk_number] = f"/api/upload/chunk/{file.id}/{chunk_number}"
            
            logger.info(f"Initialized multipart upload for file {file.id}, {total_chunks} chunks")
            
            return {
                "file_id": str(file.id),
                "upload_id": upload_id,
                "chunk_size": file.chunk_size,
                "total_chunks": total_chunks,
                "chunk_urls": chunk_urls,
                "minio_bucket": file.minio_bucket
            }
            
        except Exception as e:
            logger.error(f"Error initializing multipart upload: {e}")
            raise FileProcessingError("init_multipart_upload", str(e))
    
    async def upload_chunk(self, chunk_data: ChunkUploadDTO) -> Dict[str, Any]:
        """上传文件分块"""
        try:
            file_id = chunk_data.file_id
            upload_id = chunk_data.upload_id
            
            # 验证文件
            file = await self.repo.file_repo.get_file_by_id(file_id)
            if not file or file.upload_id != upload_id:
                raise NotFoundError("File", str(file_id), "File not found or invalid upload ID")
            
            # 验证分块编号
            if chunk_data.chunk_number < 1 or chunk_data.chunk_number > file.total_chunks:
                raise ValidationError(
                    f"Invalid chunk number: {chunk_data.chunk_number}",
                    {"chunk_number": chunk_data.chunk_number, "total_chunks": file.total_chunks}
                )
            
            # 验证分块大小
            if len(chunk_data.chunk_data) != chunk_data.chunk_size:
                raise ValidationError(
                    f"Chunk size mismatch: expected {chunk_data.chunk_size}, got {len(chunk_data.chunk_data)}",
                    {"expected": chunk_data.chunk_size, "actual": len(chunk_data.chunk_data)}
                )
            
            # 计算校验和
            checksum_md5 = chunk_data.checksum_md5 or calculate_md5_hash(chunk_data.chunk_data)
            
            # 这里应该是调用MinIO上传分块的逻辑
            # etag = await minio_repository.upload_chunk(...)
            etag = generate_uuid()  # 模拟ETag
            
            # 更新分块记录
            chunk = await self.repo.chunk_repo.get_chunk(file_id, chunk_data.chunk_number)
            if chunk:
                chunk.mark_uploaded(etag, get_current_time())
                chunk.checksum_md5 = checksum_md5
                chunk.checksum_sha256 = chunk_data.checksum_sha256
                await self.repo.chunk_repo.update_chunk(chunk)
                
                # 更新文件进度
                uploaded_chunks = await self.repo.chunk_repo.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
                await self.repo.file_repo.update_file(file_id, {
                    "uploaded_chunks": uploaded_chunks,
                    "upload_progress": (uploaded_chunks / file.total_chunks) * 100
                })
            
            logger.info(f"Uploaded chunk {chunk_data.chunk_number} for file {file_id}")
            
            return {
                "chunk_number": chunk_data.chunk_number,
                "etag": etag,
                "checksum_md5": checksum_md5,
                "checksum_sha256": chunk_data.checksum_sha256
            }
            
        except Exception as e:
            logger.error(f"Error uploading chunk: {e}")
            raise FileProcessingError("upload_chunk", str(e))
    
    async def complete_multipart_upload(
        self, 
        file_id: UUID, 
        upload_id: str,
        chunk_etags: Dict[int, str],
        checksum_md5: Optional[str] = None,
        checksum_sha256: Optional[str] = None
    ) -> FileMetadata:
        """完成分块上传"""
        try:
            file = await self.repo.file_repo.get_file_by_id(file_id)
            if not file or file.upload_id != upload_id:
                raise NotFoundError("File", str(file_id), "File not found or invalid upload ID")
            
            # 验证所有分块是否已上传
            uploaded_chunks = await self.repo.chunk_repo.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
            if uploaded_chunks != file.total_chunks:
                raise ValidationError(
                    f"Not all chunks uploaded: {uploaded_chunks}/{file.total_chunks}",
                    {"uploaded": uploaded_chunks, "total": file.total_chunks}
                )
            
            # 这里应该是调用MinIO完成分块上传的逻辑
            # await minio_repository.complete_multipart_upload(...)
            
            # 更新文件状态
            update_data = {
                "status": FileStatus.COMPLETED,
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256,
                "uploaded_at": get_current_time(),
                "upload_progress": 100.0
            }
            
            file = await self.repo.file_repo.update_file(file_id, update_data)
            if not file:
                raise NotFoundError("File", str(file_id), "File not found during update")
            
            # 标记所有分块为已验证
            chunks = await self.repo.chunk_repo.get_file_chunks(file_id)
            for chunk in chunks:
                chunk.mark_verified(get_current_time())
                await self.repo.chunk_repo.update_chunk(chunk)
            
            logger.info(f"Completed multipart upload for file {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error completing multipart upload: {e}")
            raise FileProcessingError("complete_multipart_upload", str(e))
    
    async def get_file(self, file_id: UUID) -> Optional[FileMetadata]:
        """获取文件"""
        return await self.repo.file_repo.get_file_by_id(file_id)
    
    async def update_file(self, file_id: UUID, update_data: FileUpdateDTO) -> Optional[FileMetadata]:
        """更新文件"""
        update_dict = update_data.dict(exclude_unset=True)
        return await self.repo.file_repo.update_file(file_id, update_dict)
    
    async def delete_file(self, file_id: UUID) -> bool:
        """删除文件"""
        # 这里应该先删除MinIO中的文件，再删除数据库记录
        # await minio_repository.delete_file(...)
        return await self.repo.file_repo.delete_file(file_id)
    
    async def list_files(
        self, 
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        page: int = 1, 
        page_size: int = 10,
        status: Optional[FileStatus] = None,
        visibility: Optional[FileVisibility] = None,
        file_type: Optional[FileType] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[List[FileMetadata], int]:
        """列出文件"""
        return await self.repo.file_repo.list_files(
            user_id, tenant_id, page, page_size, status, visibility, file_type, tags
        )
    
    async def get_upload_progress(self, file_id: UUID) -> UploadProgressDTO:
        """获取上传进度"""
        progress_data = await self.repo.chunk_repo.get_upload_progress(file_id)
        return UploadProgressDTO(**progress_data) if progress_data else None
    
    async def resume_multipart_upload(self, file_id: UUID) -> Dict[str, Any]:
        """恢复分块上传"""
        file = await self.get_file(file_id)
        if not file or not file.upload_id:
            raise NotFoundError("File", str(file_id), "File not found or not a multipart upload")
        
        # 获取缺失的分块
        uploaded_chunks = await self.repo.chunk_repo.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
        missing_chunks = list(range(uploaded_chunks + 1, file.total_chunks + 1))
        
        # 生成缺失分块的上传URL
        chunk_urls = {}
        for chunk_number in missing_chunks:
            chunk_urls[chunk_number] = f"/api/upload/chunk/{file_id}/{chunk_number}"
        
        return {
            "file_id": str(file_id),
            "upload_id": file.upload_id,
            "missing_chunks": missing_chunks,
            "chunk_urls": chunk_urls
        }
    
    async def abort_multipart_upload(self, file_id: UUID) -> bool:
        """中止分块上传"""
        file = await self.get_file(file_id)
        if not file or not file.upload_id:
            raise NotFoundError("File", str(file_id), "File not found or not a multipart upload")
        
        try:
            # 这里应该是调用MinIO中止分块上传的逻辑
            # await minio_repository.abort_multipart_upload(...)
            
            # 删除分块记录
            await self.repo.chunk_repo.delete_file_chunks(file_id)
            
            # 更新文件状态
            await self.repo.file_repo.update_file(file_id, {
                "status": FileStatus.CANCELLED,
                "upload_id": None,
                "upload_progress": 0.0
            })
            
            return True
        except Exception as e:
            logger.error(f"Error aborting multipart upload: {e}")
            return False
    
    async def get_user_files_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户文件统计"""
        return await self.repo.file_repo.get_user_files_stats(user_id)

# 服务工厂
class ServiceFactory:
    """服务工厂"""
    
    def __init__(self, repository_manager: RepositoryManager):
        self.repository_manager = repository_manager
        self._file_service = None
        self._upload_task_service = None
    
    @property
    def file_service(self) -> FileService:
        """获取文件服务"""
        if self._file_service is None:
            self._file_service = FileService(self.repository_manager)
        return self._file_service
    
    # 其他服务实例化...

# 全局服务实例
_service_factory = None

def init_services(motor_client):
    """初始化服务"""
    global _service_factory
    repository_manager = RepositoryManager(motor_client)
    _service_factory = ServiceFactory(repository_manager)
    return _service_factory

def get_file_service() -> FileService:
    """获取文件服务实例"""
    if _service_factory is None:
        raise RuntimeError("Services not initialized. Call init_services first.")
    return _service_factory.file_service