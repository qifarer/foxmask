# -*- coding: utf-8 -*-
# foxmask/file/repositories.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# Repository for database operations

from typing import Optional, List, Dict, Any, Tuple
from datetime import timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

from bson import ObjectId

from foxmask.core.config import settings
from foxmask.file.models import File, FileChunk, FileStatus, ChunkStatus, FileVisibility, FileType
from foxmask.utils.minio_client import minio_client
from foxmask.utils.helpers import get_current_time, generate_uuid
from foxmask.core.exceptions import NotFoundError, ExternalServiceError
from foxmask.core.logger import logger

class FileRepository:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _run_in_thread(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def get_file_by_id(self, file_id: str) -> Optional[File]:
        try:
            if not ObjectId.is_valid(file_id):
                return None
            return await File.get(file_id)
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {e}")
            raise
    
    async def get_file_by_file_id(self, file_id: str) -> Optional[File]:
        try:
            return await File.find_one(File.file_id == file_id)
        except Exception as e:
            logger.error(f"Error getting file by file_id {file_id}: {e}")
            raise
    
    async def save_file(self, file: File) -> File:
        try:
            await file.save()
            return file
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise
    
    async def create_file(self, file_data: Dict[str, Any]) -> File:
        try:
            file = File(**file_data)
            await file.insert()
            return file
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        try:
            file = await self.get_file_by_id(file_id)
            if file:
                await file.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            raise
    
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
    ) -> Tuple[List[File], int]:
        try:
            query = File.find()
            
            if user_id:
                query = query.find(File.uploaded_by == user_id)
            
            if tenant_id:
                query = query.find(File.tenant_id == tenant_id)
            
            if status:
                query = query.find(File.status == status)
            
            if visibility:
                query = query.find(File.visibility == visibility)
            
            if file_type:
                query = query.find(File.file_type == file_type)
            
            if tags:
                query = query.find(File.tags.in_(tags))
            
            query = query.sort(-File.created_at)
            
            total_count = await query.count()
            files = await query.skip((page - 1) * page_size).limit(page_size).to_list()
            
            return files, total_count
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def update_file(self, file_id: str, update_data: Dict[str, Any]) -> Optional[File]:
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                return None
            
            for field, value in update_data.items():
                if hasattr(file, field):
                    setattr(file, field, value)
            
            file.updated_at = get_current_time()
            await file.save()
            return file
        except Exception as e:
            logger.error(f"Error updating file {file_id}: {e}")
            raise
    
    async def update_file_status(self, file_id: str, status: FileStatus) -> Optional[File]:
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                return None
            
            file.status = status
            file.updated_at = get_current_time()
            await file.save()
            return file
        except Exception as e:
            logger.error(f"Error updating file status {file_id}: {e}")
            raise
    
    async def increment_download_count(self, file_id: str) -> Optional[File]:
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                return None
            
            file.download_count += 1
            file.last_downloaded_at = get_current_time()
            file.updated_at = get_current_time()
            await file.save()
            return file
        except Exception as e:
            logger.error(f"Error incrementing download count {file_id}: {e}")
            raise
    
    async def increment_view_count(self, file_id: str) -> Optional[File]:
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                return None
            
            file.view_count += 1
            file.last_viewed_at = get_current_time()
            file.updated_at = get_current_time()
            await file.save()
            return file
        except Exception as e:
            logger.error(f"Error incrementing view count {file_id}: {e}")
            raise
    
    async def get_user_files_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            total_files = await File.find(File.uploaded_by == user_id).count()
            
            total_size_pipeline = [
                {"$match": {"uploaded_by": user_id}},
                {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
            ]
            total_size_result = await File.aggregate(total_size_pipeline).to_list()
            total_size = total_size_result[0]["total_size"] if total_size_result else 0
            
            status_counts = {}
            for status in FileStatus:
                count = await File.find(
                    File.uploaded_by == user_id,
                    File.status == status
                ).count()
                status_counts[status.value] = count
            
            type_counts = {}
            for file_type in FileType:
                count = await File.find(
                    File.uploaded_by == user_id,
                    File.file_type == file_type
                ).count()
                type_counts[file_type.value] = count
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "status_counts": status_counts,
                "type_counts": type_counts
            }
        except Exception as e:
            logger.error(f"Error getting user files stats {user_id}: {e}")
            raise

    async def create_chunk(self, chunk_data: Dict[str, Any]) -> FileChunk:
        try:
            chunk = FileChunk(**chunk_data)
            await chunk.insert()
            return chunk
        except Exception as e:
            logger.error(f"Error creating chunk: {e}")
            raise
    
    async def create_chunks(self, chunks: List[FileChunk]) -> None:
        try:
            await FileChunk.bulk_insert(chunks)
        except Exception as e:
            logger.error(f"Error creating chunks: {e}")
            raise
    
    async def get_chunk(self, file_id: str, chunk_number: int) -> Optional[FileChunk]:
        try:
            return await FileChunk.find_one(
                FileChunk.file_id == file_id,
                FileChunk.chunk_number == chunk_number
            )
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_number} for file {file_id}: {e}")
            raise
    
    async def get_file_chunks(self, file_id: str, page: int = 1, page_size: int = 50) -> List[FileChunk]:
        try:
            return await FileChunk.find(FileChunk.file_id == file_id).sort(FileChunk.chunk_number).skip((page - 1) * page_size).limit(page_size).to_list()
        except Exception as e:
            logger.error(f"Error getting chunks for file {file_id}: {e}")
            raise
    
    async def update_chunk(self, chunk: FileChunk) -> FileChunk:
        try:
            await chunk.save()
            return chunk
        except Exception as e:
            logger.error(f"Error updating chunk {chunk.chunk_number}: {e}")
            raise
    
    async def update_chunk_status(self, file_id: str, chunk_number: int, status: ChunkStatus, error_message: Optional[str] = None) -> Optional[FileChunk]:
        try:
            chunk = await self.get_chunk(file_id, chunk_number)
            if not chunk:
                return None
            
            chunk.status = status
            if error_message:
                chunk.error_message = error_message
            
            if status == ChunkStatus.UPLOADED:
                chunk.uploaded_at = get_current_time()
            elif status == ChunkStatus.VERIFIED:
                chunk.verified_at = get_current_time()
            
            await chunk.save()
            return chunk
        except Exception as e:
            logger.error(f"Error updating chunk status {file_id}:{chunk_number}: {e}")
            raise
    
    async def delete_file_chunks(self, file_id: str) -> int:
        try:
            result = await FileChunk.find(FileChunk.file_id == file_id).delete()
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting chunks for file {file_id}: {e}")
            raise
    
    async def count_chunks_by_status(self, file_id: str, status: ChunkStatus) -> int:
        try:
            return await FileChunk.find(
                FileChunk.file_id == file_id,
                FileChunk.status == status
            ).count()
        except Exception as e:
            logger.error(f"Error counting chunks by status for file {file_id}: {e}")
            raise
    
    async def count_file_chunks(self, file_id: str) -> int:
        try:
            return await FileChunk.find(FileChunk.file_id == file_id).count()
        except Exception as e:
            logger.error(f"Error counting chunks for file {file_id}: {e}")
            raise
    
    async def get_upload_progress(self, file_id: str) -> Dict[str, Any]:
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                raise NotFoundError(f"File {file_id} not found")
            
            uploaded_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
            verified_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.VERIFIED)
            
            progress_percentage = 0.0
            if file.total_chunks > 0:
                progress_percentage = (uploaded_chunks / file.total_chunks) * 100
            
            return {
                "file_id": file_id,
                "filename": file.filename,
                "status": file.status,
                "uploaded_chunks": uploaded_chunks,
                "verified_chunks": verified_chunks,
                "total_chunks": file.total_chunks,
                "progress_percentage": progress_percentage
            }
        except Exception as e:
            logger.error(f"Error getting upload progress for file {file_id}: {e}")
            raise

class MinIORepository:
    """Repository for MinIO storage operations"""
    
    def __init__(self):
        self.minio = minio_client
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous MinIO operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def _get_tenant_bucket_name(self, tenant_id: str) -> str:
        """获取租户对应的存储桶名称"""
        if not settings.MINIO_USE_TENANT_BUCKETS:
            return settings.MINIO_DEFAULT_BUCKET
        
        # 清理租户ID，确保符合存储桶命名规范
        clean_tenant_id = tenant_id.replace('_', '-').lower()
        bucket_name = f"{settings.MINIO_BUCKET_PREFIX}-{clean_tenant_id}"
        
        # 确保存储桶存在
        await self._ensure_bucket_exists(bucket_name)
        return bucket_name
    
    async def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """确保存储桶存在"""
        try:
            # 检查存储桶是否存在
            exists = await self._run_in_thread(self.minio.bucket_exists, bucket_name)
            if not exists:
                # 创建存储桶
                await self._run_in_thread(self.minio.make_bucket, bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error ensuring bucket exists {bucket_name}: {e}")
            raise ExternalServiceError("MinIO", "ensure_bucket_exists", str(e))
        
    
    async def _get_tenant_bucket_name_from_file(self, file_id: str) -> str:
        try:
            file = await File.get(file_id)
            if file:
                return file.minio_bucket
            return settings.MINIO_DEFAULT_BUCKET
        except:
            return settings.MINIO_DEFAULT_BUCKET
    
    async def _generate_object_name(self, tenant_id: str, user_id: str, filename: str) -> str:
        from datetime import datetime
        
        now = datetime.now()
        extension = self._get_file_extension(filename)
        unique_id = generate_uuid()[:8]
        
        if settings.FILE_STORAGE_PATH_FORMAT:
            object_name = settings.FILE_STORAGE_PATH_FORMAT.format(
                tenant_id=tenant_id,
                user_id=user_id,
                year=now.year,
                month=f"{now.month:02d}",  # 补齐 2 位
                day=f"{now.day:02d}",      # 补齐 2 位
                filename=f"{int(now.timestamp())}_{unique_id}.{extension}" if extension else f"{int(now.timestamp())}_{unique_id}"
            )
        else:
            object_name = f"{tenant_id}/{now.year}/{now.month:02d}/{now.day:02d}/{int(now.timestamp())}_{unique_id}"
            if extension:
                object_name += f".{extension}"
        
        return object_name
    
    def _get_file_extension(self, filename: str) -> str:
        if not filename or '.' not in filename:
            return ''
        
        parts = filename.rsplit('.', 2)
        if len(parts) > 2 and parts[-2].lower() == 'tar':
            return 'tar.gz'
        return parts[-1].lower()
    
    async def initiate_multipart_upload(self, tenant_id: str, object_name: str) -> str:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            return await self._run_in_thread(
                self.minio.create_multipart_upload,
                bucket_name,
                object_name
            )
        except Exception as e:
            logger.error(f"MinIO multipart upload initiation failed: {e}")
            raise ExternalServiceError("MinIO", "initiate_multipart_upload", str(e))
    
    async def generate_chunk_upload_url(
        self, tenant_id: str, object_name: str, upload_id: str, chunk_number: int, expires: timedelta
    ) -> str:
        print(f"Generating chunk upload URL for tenant_id: {tenant_id}, object_name: {object_name}, upload_id: {upload_id}, chunk_number: {chunk_number}, expires: {expires}")
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        print(f"Using bucket name: {bucket_name}")
        try:
            return await self._run_in_thread(
                self.minio.presign_upload_part_url,
                bucket_name,
                object_name=object_name,
                upload_id=upload_id,
                part_number=chunk_number,
                expires=expires
            )
        except Exception as e:
            logger.error(f"Failed to generate chunk upload URL: {e}")
            raise ExternalServiceError("MinIO", "generate_upload_url", str(e))
    
    async def upload_chunk(
        self, tenant_id: str, object_name: str, upload_id: str, chunk_number: int, chunk_data: bytes, checksum_md5: Optional[str] = None
    ) -> str:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            return await self._run_in_thread(
                self.minio.upload_part,
                bucket_name,
                object_name,
                upload_id,
                chunk_number,
                chunk_data,
                checksum_md5
            )
        except Exception as e:
            logger.error(f"MinIO chunk upload failed: {e}")
            raise ExternalServiceError("MinIO", "upload_chunk", str(e))
    
    async def complete_multipart_upload(
        self, tenant_id: str, object_name: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> None:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.complete_multipart_upload,
                bucket_name,
                object_name,
                upload_id,
                parts
            )
        except Exception as e:
            logger.error(f"MinIO multipart upload completion failed: {e}")
            raise ExternalServiceError("MinIO", "complete_multipart_upload", str(e))
    
    async def abort_multipart_upload(self, tenant_id: str, object_name: str, upload_id: str) -> None:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.abort_multipart_upload,
                bucket_name,
                object_name,
                upload_id
            )
        except Exception as e:
            logger.error(f"MinIO multipart upload abortion failed: {e}")
            raise ExternalServiceError("MinIO", "abort_multipart_upload", str(e))
    
    async def upload_file(self, tenant_id: str, object_name: str, content: bytes) -> None:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.upload_file,
                bucket_name,
                object_name,
                content
            )
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise ExternalServiceError("MinIO", "upload_file", str(e))
    
    async def download_file(self, tenant_id: str, object_name: str) -> bytes:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            return await self._run_in_thread(
                self.minio.download_file,
                bucket_name,
                object_name
            )
        except Exception as e:
            logger.error(f"MinIO download failed: {e}")
            raise ExternalServiceError("MinIO", "download_file", str(e))
    
    async def delete_file(self, tenant_id: str, object_name: str) -> None:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.delete_object,
                bucket_name,
                object_name
            )
        except Exception as e:
            logger.error(f"MinIO delete failed: {e}")
            raise ExternalServiceError("MinIO", "delete_file", str(e))
    
    async def generate_download_url(self, tenant_id: str, object_name: str, expires: timedelta) -> str:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            return await self._run_in_thread(
                self.minio.presign_get_object,
                bucket_name,
                object_name,
                expires=expires
            )
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise ExternalServiceError("MinIO", "generate_download_url", str(e))
    
    async def file_exists(self, tenant_id: str, object_name: str) -> bool:
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.stat_object,
                bucket_name,
                object_name
            )
            return True
        except Exception:
            return False

file_repository = FileRepository()
minio_repository = MinIORepository()