# app/domains/file/services.py (增强版)
from typing import List, Optional
from datetime import datetime
from minio.error import S3Error
from foxmask.core.minio import get_minio_client, ensure_bucket_exists
from foxmask.core.database import get_database
from foxmask.core.exceptions import NotFoundError, ServiceError
from foxmask.file.models import FileMetadata, FileStatus
from foxmask.core.config import get_settings
from foxmask.core.tracking import tracking_service, track_performance
from foxmask.auth.schemas import User

settings = get_settings()

class FileService:
    def __init__(self):
        self.db = get_database()
        self.minio_client = get_minio_client()
    
    @track_performance("file_initiate_upload")
    async def initiate_upload(self, filename: str, size: int, content_type: str, owner: str, user: User) -> str:
        file_meta = FileMetadata(
            filename=filename,
            size=size,
            content_type=content_type,
            owner=owner
        )
        
        await self.db.files.insert_one(file_meta.dict())
        
        # 记录文件上传初始化事件
        await tracking_service.log_file_operation(
            operation="upload_initiate",
            file_id=file_meta.id,
            filename=filename,
            user=user,
            details={
                "size": size,
                "content_type": content_type
            }
        )
        
        return file_meta.id
    
    @track_performance("file_upload_chunk")
    async def upload_chunk(self, file_id: str, chunk_index: int, chunk_data: bytes, owner: str, user: User):
        file_meta = await self.get_file(file_id, owner)
        if not file_meta:
            raise NotFoundError("File not found")
        
        await ensure_bucket_exists(self.minio_client)
        chunk_key = f"chunks/{file_id}/{chunk_index}"
        
        try:
            self.minio_client.put_object(
                settings.MINIO_BUCKET,
                chunk_key,
                chunk_data,
                len(chunk_data)
            )
            
            # 记录分块上传事件
            await tracking_service.log_file_operation(
                operation="upload_chunk",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                details={
                    "chunk_index": chunk_index,
                    "chunk_size": len(chunk_data)
                }
            )
            
        except S3Error as e:
            # 记录上传失败事件
            await tracking_service.log_file_operation(
                operation="upload_chunk",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                success=False,
                details={
                    "chunk_index": chunk_index,
                    "error": str(e)
                }
            )
            raise ServiceError(f"Chunk upload failed: {e}")
    
    @track_performance("file_complete_upload")
    async def complete_upload(self, file_id: str, owner: str, user: User) -> FileMetadata:
        file_meta = await self.get_file(file_id, owner)
        if not file_meta:
            raise NotFoundError("File not found")
        
        # Combine chunks into final file
        await self._combine_chunks(file_id)
        
        # Update metadata
        file_meta.status = FileStatus.UPLOADED
        file_meta.processed_at = datetime.utcnow()
        
        await self.db.files.update_one(
            {"id": file_id},
            {"$set": file_meta.dict()}
        )
        
        # 记录上传完成事件
        await tracking_service.log_file_operation(
            operation="upload_complete",
            file_id=file_id,
            filename=file_meta.filename,
            user=user,
            details={
                "size": file_meta.size,
                "status": file_meta.status
            }
        )
        
        return file_meta
    
    async def _combine_chunks(self, file_id: str):
        # Implementation for combining chunks
        # This would retrieve all chunks and combine them into a single file
        pass
    
    @track_performance("file_get")
    async def get_file(self, file_id: str, owner: str) -> Optional[FileMetadata]:
        data = await self.db.files.find_one({"id": file_id, "owner": owner})
        if data:
            return FileMetadata(**data)
        return None
    
    @track_performance("file_list")
    async def list_files(self, owner: str, skip: int = 0, limit: int = 100) -> List[FileMetadata]:
        cursor = self.db.files.find({"owner": owner}).skip(skip).limit(limit)
        return [FileMetadata(**doc) async for doc in cursor]
    
    @track_performance("file_get_presigned_url")
    async def get_presigned_url(self, file_id: str, owner: str, user: User, expires: int = 3600) -> str:
        file_meta = await self.get_file(file_id, owner)
        if not file_meta:
            raise NotFoundError("File not found")
        
        try:
            url = self.minio_client.presigned_get_object(
                settings.MINIO_BUCKET,
                file_id,
                expires=expires
            )
            
            # 记录文件下载事件
            await tracking_service.log_file_operation(
                operation="download",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                details={
                    "expires": expires,
                    "url": url
                }
            )
            
            return url
        except S3Error as e:
            # 记录下载失败事件
            await tracking_service.log_file_operation(
                operation="download",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                success=False,
                details={
                    "error": str(e)
                }
            )
            raise ServiceError(f"Failed to generate presigned URL: {e}")
    
    @track_performance("file_delete")
    async def delete_file(self, file_id: str, owner: str, user: User):
        file_meta = await self.get_file(file_id, owner)
        if not file_meta:
            raise NotFoundError("File not found")
        
        try:
            # Delete from MinIO
            self.minio_client.remove_object(settings.MINIO_BUCKET, file_id)
            
            # Delete metadata
            await self.db.files.delete_one({"id": file_id, "owner": owner})
            
            # 记录文件删除事件
            await tracking_service.log_file_operation(
                operation="delete",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                details={
                    "size": file_meta.size,
                    "content_type": file_meta.content_type
                }
            )
            
        except S3Error as e:
            # 记录删除失败事件
            await tracking_service.log_file_operation(
                operation="delete",
                file_id=file_id,
                filename=file_meta.filename,
                user=user,
                success=False,
                details={
                    "error": str(e)
                }
            )
            raise ServiceError(f"Failed to delete file: {e}")