from minio.error import S3Error
from minio.commonconfig import CopySource
from typing import Optional, List, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
from datetime import datetime, timedelta
import math
from io import BytesIO
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from foxmask.core.config import settings
from .models import File, FileChunk, FileStatus, ChunkStatus, FileVisibility, FileType, EXTENSION_FILE_TYPES
from .schemas import FileUploadInitRequest
from foxmask.utils.minio_client import minio_client
from foxmask.utils.helpers import calculate_md5_hash, generate_uuid
from foxmask.core.exceptions import (
    FileProcessingError, NotFoundError, ValidationError, 
    ExternalServiceError, RetryableError
)
from foxmask.core.logger import logger, log_exception
from foxmask.core.monitoring import monitoring_service
from foxmask.core.audit import audit_service, AuditAction, AuditResourceType
from foxmask.utils.helpers import get_current_time

class FileService:
    def __init__(self):
        self.minio = minio_client
        self.chunk_size = 5 * 1024 * 1024  # 5MB default chunk size
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def _run_in_thread(self, func, *args, **kwargs):
        """Run synchronous MinIO operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))

    async def init_multipart_upload(self, file_data: FileUploadInitRequest, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Initialize multipart upload"""
        try:
            filename = file_data.filename
            file_size = file_data.file_size
            content_type = file_data.content_type or "application/octet-stream"
            chunk_size = file_data.chunk_size or self.chunk_size
            
            # Calculate total chunks
            total_chunks = math.ceil(file_size / chunk_size)
            
            # 生成唯一 object name
            minio_object_name = self._generate_minio_object_name(filename)
            
            # 提取文件扩展名
            file_extension = self._get_file_extension(filename)
            
            # 确定文件类型
            file_type = self._determine_file_type(filename, file_extension, content_type)
            
            # 处理可见性字段
            visibility = FileVisibility.PRIVATE
            if hasattr(file_data, 'visibility') and file_data.visibility:
                try:
                    visibility = FileVisibility(file_data.visibility.lower())
                except ValueError:
                    visibility = FileVisibility.PRIVATE
            
            # 创建文件元数据
            file_kwargs = {
                # 必需字段
                'filename': filename,
                'file_size': file_size,
                'content_type': content_type,
                'extension': file_extension,
                'minio_object_name': minio_object_name,
                'minio_bucket': settings.MINIO_BUCKET_NAME or "foxmask",
                'uploaded_by': user_id,
                'tenant_id': tenant_id,
                
                # 可选字段
                'file_type': file_type,
                'status': FileStatus.UPLOADING,
                'upload_progress': 0.0,
                'visibility': visibility,
                'allowed_users': getattr(file_data, 'allowed_users', []),
                'allowed_roles': getattr(file_data, 'allowed_roles', []),
                'tags': getattr(file_data, 'tags', []),
                'categories': [],
                'description': getattr(file_data, 'description', None),
                'metadata': getattr(file_data, 'metadata', {}),
                'is_multipart': True,
                'upload_id': "",
                'chunk_size': chunk_size,
                'total_chunks': total_chunks,
                'uploaded_chunks': 0,
                'verified_chunks': 0,
                'created_at': get_current_time(),
                'updated_at': get_current_time(),
                'version': 1,
                'is_latest': True,
                'download_count': 0,
                'view_count': 0
            }
            
            # 移除 None 值
            file_kwargs = {k: v for k, v in file_kwargs.items() if v is not None}
            
            # 创建 File 对象
            file_metadata = File(**file_kwargs)
            
            await file_metadata.insert()
            
            # Initiate multipart upload with MinIO
            upload_id = await self._initiate_minio_multipart_upload(file_metadata.minio_object_name)
            
            # 更新 upload_id
            file_metadata.upload_id = upload_id
            file_metadata.updated_at = get_current_time()
            await file_metadata.save()
            
            # Generate presigned URLs for all chunks
            chunk_urls = {}
            for chunk_number in range(1, total_chunks + 1):
                url = await self._generate_chunk_upload_url(
                    file_metadata.minio_object_name, upload_id, chunk_number
                )
                chunk_urls[chunk_number] = url
            
            # Create chunk records
            await self._create_chunk_records(str(file_metadata.id), upload_id, total_chunks, chunk_size)
            
            return {
                "file_id": str(file_metadata.id),
                "upload_id": upload_id,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "chunk_urls": chunk_urls,
                "minio_bucket": file_metadata.minio_bucket  # 添加这个字段
            }
        
        except Exception as e:
            logger.error(f"Error initializing multipart upload: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize upload: {e}"
            )

    def _determine_file_type(self, filename: str, extension: str, content_type: str) -> FileType:
        """Determine file type based on extension and content type"""
        # 优先使用扩展名查找
        if extension and extension in EXTENSION_FILE_TYPES:
            return EXTENSION_FILE_TYPES[extension]
        
        # 回退到内容类型
        content_type = content_type.lower() if content_type else ''
        
        if any(x in content_type for x in ['pdf', 'document', 'msword', 'wordprocessing']):
            return FileType.PDF if 'pdf' in content_type else FileType.DOCUMENT
        elif any(x in content_type for x in ['spreadsheet', 'excel']):
            return FileType.SPREADSHEET
        elif any(x in content_type for x in ['presentation', 'powerpoint']):
            return FileType.PRESENTATION
        elif any(x in content_type for x in ['text/', 'markdown']):
            return FileType.TEXT
        elif content_type.startswith('image/'):
            return FileType.IMAGE if 'svg' not in content_type else FileType.VECTOR
        elif content_type.startswith('audio/'):
            return FileType.AUDIO
        elif content_type.startswith('video/'):
            return FileType.VIDEO
        elif 'json' in content_type:
            return FileType.JSON
        elif 'xml' in content_type:
            return FileType.XML
        elif 'csv' in content_type:
            return FileType.CSV
        elif any(x in content_type for x in ['zip', 'rar', 'tar', 'gzip', 'compress']):
            return FileType.ARCHIVE
        
        return FileType.UNKNOWN

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if not filename or '.' not in filename:
            return ''
        
        # 处理复杂扩展名如 .tar.gz
        parts = filename.rsplit('.', 2)
        if len(parts) > 2 and parts[-2].lower() == 'tar':
            return 'tar.gz'
        
        return parts[-1].lower()

    def _generate_minio_object_name(self, filename: str) -> str:
        """Generate unique MinIO object name"""
        import uuid
        from datetime import datetime
        
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = self._get_file_extension(filename)
        
        return f"{timestamp}_{unique_id}.{file_extension}" if file_extension else f"{timestamp}_{unique_id}"

    async def _create_chunk_records(self, file_id: str, upload_id: str, total_chunks: int, chunk_size: int) -> None:
        """Create chunk records for a file"""
        file_metadata = await File.get(file_id)
        if not file_metadata:
            raise NotFoundError("File", file_id, "File not found")
        
        chunks = []
        for chunk_number in range(1, total_chunks + 1):
            start_byte = (chunk_number - 1) * chunk_size
            end_byte = min(start_byte + chunk_size, file_metadata.file_size) - 1
            
            chunk = FileChunk(
                file_id=file_id,
                upload_id=upload_id,
                chunk_number=chunk_number,
                chunk_size=chunk_size,
                start_byte=start_byte,
                end_byte=end_byte,
                minio_object_name=f"{upload_id}/part-{chunk_number}",
                minio_bucket=settings.MINIO_BUCKET_NAME or "foxmask",
                status=ChunkStatus.PENDING
            )
            chunks.append(chunk)
        
        await FileChunk.insert_many(chunks)

    async def upload_chunk(
        self,
        file_id: str,
        upload_id: str,
        chunk_number: int,
        chunk_data: bytes,
        chunk_size: int,
        checksum_md5: Optional[str] = None,
        checksum_sha256: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a single chunk with enhanced error handling"""
        start_time = get_current_time()
        
        try:
            # 验证 chunk_size 与实际数据长度是否一致
            actual_size = len(chunk_data)
            if chunk_size != actual_size:
                raise ValidationError(
                    f"Chunk size mismatch: expected {chunk_size}, got {actual_size}",
                    {"expected_size": chunk_size, "actual_size": actual_size}
                )
            
            # Get file metadata
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata or file_metadata.upload_id != upload_id:
                raise NotFoundError("File", file_id, "File not found or invalid upload ID")
            
            # Validate chunk number
            if chunk_number < 1 or chunk_number > file_metadata.total_chunks:
                raise ValidationError(
                    f"Invalid chunk number: {chunk_number}. Must be between 1 and {file_metadata.total_chunks}",
                    {"chunk_number": chunk_number, "total_chunks": file_metadata.total_chunks}
                )
            
            # Calculate checksums if not provided
            if not checksum_md5:
                checksum_md5 = calculate_md5_hash(chunk_data)
            
            # Upload chunk to MinIO - 注释掉有问题的监控代码
            # with monitoring_service.time_operation("minio_chunk_upload"):
            etag = await self._upload_chunk_to_minio(
                file_metadata.minio_object_name,
                upload_id,
                chunk_number,
                chunk_data,
                checksum_md5
            )
            
            # Update chunk record
            chunk = await FileChunk.find_one(
                FileChunk.file_id == file_id,
                FileChunk.chunk_number == chunk_number
            )
            
            if chunk:
                chunk.mark_uploaded(etag, get_current_time())
                chunk.checksum_md5 = checksum_md5
                chunk.checksum_sha256 = checksum_sha256
                await chunk.save()
                
                # Update file metadata
                file_metadata.uploaded_chunks += 1
                file_metadata.update_progress(file_metadata.uploaded_chunks, file_metadata.verified_chunks)
                await file_metadata.save()
            
            # Log audit event
            audit_service.log(
                AuditAction.UPLOAD,
                AuditResourceType.FILE,
                file_id,
                file_metadata.uploaded_by,
                {
                    "chunk_number": chunk_number,
                    "chunk_size": chunk_size,
                    "operation": "chunk_upload"
                }
            )
            
            duration = (get_current_time() - start_time).total_seconds() * 1000
            logger.info(
                f"Chunk {chunk_number} uploaded successfully for file {file_id}",
                {
                    "chunk_number": chunk_number,
                    "file_id": file_id,
                    "chunk_size": chunk_size,
                    "duration_ms": duration
                }
            )
            
            # 计算字节位置
            start_byte = (chunk_number - 1) * chunk_size
            end_byte = chunk_number * chunk_size
            
            return {
                "chunk_number": chunk_number,
                "etag": etag,
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256,
                "chunk_size": chunk_size,
                "start_byte": start_byte,
                "end_byte": end_byte
            }
            
        except ValidationError:
            raise  # Re-raise known exceptions
            
        except Exception as e:
            duration = (get_current_time() - start_time).total_seconds() * 1000
            log_exception(
                logger,
                e,
                {
                    "operation": "chunk_upload",
                    "file_id": file_id,
                    "chunk_number": chunk_number,
                    "chunk_size": chunk_size,
                    "duration_ms": duration
                }
            )
            
            # Convert to appropriate exception type
            if isinstance(e, S3Error):
                raise ExternalServiceError("MinIO", "chunk_upload", str(e))
            else:
                raise FileProcessingError("chunk_upload", str(e))

    async def complete_multipart_upload(
        self,
        file_id: str,
        upload_id: str,
        chunk_etags: Dict[int, str],
        checksum_md5: Optional[str] = None,  # 添加这个参数
        checksum_sha256: Optional[str] = None  # 添加这个参数
    ) -> File:
        """Complete multipart upload and assemble file"""
        try:
            # Get file metadata
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata or file_metadata.upload_id != upload_id:
                raise HTTPException(status_code=404, detail="File not found or invalid upload ID")
            
            # Verify all chunks are uploaded
            uploaded_chunks = await FileChunk.find(
                FileChunk.file_id == file_id,
                FileChunk.status == ChunkStatus.UPLOADED
            ).count()
            
            if uploaded_chunks != file_metadata.total_chunks:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not all chunks uploaded. {uploaded_chunks}/{file_metadata.total_chunks} chunks ready"
                )
            
            # Complete multipart upload in MinIO - 使用正确的键名
            parts = []
            for chunk_number in range(1, file_metadata.total_chunks + 1):
                if chunk_number not in chunk_etags:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing ETag for chunk {chunk_number}"
                    )
                parts.append({
                    "PartNumber": chunk_number,  # MinIO 期望的键名
                    "ETag": chunk_etags[chunk_number]  # MinIO 期望的键名
                })
            
            # Sort parts by part number
            parts.sort(key=lambda x: x["PartNumber"])
            
            await self._complete_minio_multipart_upload(
                file_metadata.minio_object_name,
                upload_id,
                parts
            )

            '''
            # Verify file integrity - 使用传入的校验和或重新计算
            if checksum_md5:
                # 如果传入了校验和，进行验证
                file_checksum = await self._verify_file_integrity(file_id)
                if file_checksum != checksum_md5:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File integrity check failed. Expected {checksum_md5}, got {file_checksum}"
                    )
                file_metadata.checksum_md5 = checksum_md5
            else:
                # 如果没有传入，重新计算
                file_checksum = await self._verify_file_integrity(file_id)
                file_metadata.checksum_md5 = file_checksum
            '''
            file_metadata.checksum_md5 = checksum_md5
            # 设置 SHA256 校验和（如果提供）
            if checksum_sha256:
                file_metadata.checksum_sha256 = checksum_sha256
            
            file_metadata.update_status(FileStatus.UPLOADED)
            file_metadata.uploaded_at = get_current_time()
            await file_metadata.save()
            print(f"file_metadata:, {file_metadata.model_dump}")
            # Update all chunks to verified status
            chunks = await FileChunk.find(FileChunk.file_id == file_id).to_list()
            for chunk in chunks:
                chunk.mark_verified(get_current_time())
                await chunk.save()
                print(f"chunks:, {str(chunk)}")
                
            logger.info(f"Multipart upload completed for file {file_id}")
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error completing multipart upload for file {file_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete upload: {e}"
            )

    async def get_upload_progress(self, file_id: str) -> Dict[str, Any]:
        """Get upload progress for a file"""
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        uploaded_chunks = await FileChunk.find(
            FileChunk.file_id == file_id,
            FileChunk.status.in_([ChunkStatus.UPLOADED, ChunkStatus.VERIFIED])
        ).count()
        
        return {
            "file_id": file_id,
            "filename": file_metadata.filename,
            "status": file_metadata.status,
            "uploaded_chunks": uploaded_chunks,
            "total_chunks": file_metadata.total_chunks,
            "progress_percentage": file_metadata.upload_progress
        }

    async def resume_multipart_upload(self, file_id: str) -> Dict[str, Any]:
        """Resume a multipart upload"""
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata or not file_metadata.upload_id:
            raise HTTPException(status_code=404, detail="File not found or not a multipart upload")
        
        # Find missing chunks
        uploaded_chunks = await FileChunk.find(
            FileChunk.file_id == file_id,
            FileChunk.status.in_([ChunkStatus.UPLOADED, ChunkStatus.VERIFIED])
        ).to_list()
        
        uploaded_chunk_numbers = {chunk.chunk_number for chunk in uploaded_chunks}
        all_chunk_numbers = set(range(1, file_metadata.total_chunks + 1))
        missing_chunks = sorted(all_chunk_numbers - uploaded_chunk_numbers)
        
        # Generate URLs for missing chunks
        chunk_urls = {}
        for chunk_number in missing_chunks:
            url = await self._generate_chunk_upload_url(
                file_metadata.minio_object_name,
                file_metadata.upload_id,
                chunk_number
            )
            chunk_urls[chunk_number] = url
        
        return {
            "file_id": file_id,
            "upload_id": file_metadata.upload_id,
            "missing_chunks": missing_chunks,
            "chunk_urls": chunk_urls
        }

    async def abort_multipart_upload(self, file_id: str) -> bool:
        """Abort a multipart upload and clean up"""
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata or not file_metadata.upload_id:
            raise HTTPException(status_code=404, detail="File not found or not a multipart upload")
        
        try:
            # Abort multipart upload in MinIO
            await self._abort_minio_multipart_upload(
                file_metadata.minio_object_name,
                file_metadata.upload_id
            )
            
            # Delete chunk records
            await FileChunk.find(FileChunk.file_id == file_id).delete()
            
            # Update file status
            file_metadata.update_status(FileStatus.FAILED)
            file_metadata.upload_id = None
            await file_metadata.save()
            
            logger.info(f"Multipart upload aborted for file {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error aborting multipart upload for file {file_id}: {e}")
            return False

    # MinIO helper methods
    async def _initiate_minio_multipart_upload(self, object_name: str) -> str:
        """Initiate multipart upload with MinIO"""
        try:
            return await self._run_in_thread(
                self.minio.create_multipart_upload,
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload initiation failed: {e}")
            raise

    async def _generate_chunk_upload_url(
        self, object_name: str, upload_id: str, chunk_number: int
    ) -> str:
        """Generate presigned URL for chunk upload"""
        try:
            return await self._run_in_thread(
                self.minio.presign_url,
                "upload_part",
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name,
                upload_id=upload_id,
                part_number=chunk_number,
                expires=timedelta(hours=24)
            )
        except S3Error as e:
            logger.error(f"Failed to generate chunk upload URL: {e}")
            raise

    async def _upload_chunk_to_minio(
        self, object_name: str, upload_id: str, chunk_number: int, 
        chunk_data: bytes, checksum_md5: str
    ) -> str:
        """Upload chunk to MinIO"""
        try:
            return await self._run_in_thread(
                self.minio.upload_part,
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name,
                upload_id,
                chunk_number,
                chunk_data,
                checksum_md5
            )
        except S3Error as e:
            logger.error(f"MinIO chunk upload failed: {e}")
            raise

    async def _complete_minio_multipart_upload(
        self, object_name: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> None:
        print(f"complete_minio_multipart_upload Call: start:{str(parts)}")
        """Complete multipart upload in MinIO"""
        try:
            await self._run_in_thread(
                self.minio.complete_multipart_upload,
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name,
                upload_id,
                parts
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload completion failed: {e}")
            raise

    async def _abort_minio_multipart_upload(self, object_name: str, upload_id: str) -> None:
        """Abort multipart upload in MinIO"""
        try:
            await self._run_in_thread(
                self.minio.abort_multipart_upload,
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name,
                upload_id
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload abortion failed: {e}")
            raise

    async def _verify_file_integrity(self, file_id: str) -> str:
        """Verify file integrity and return actual checksum"""
        try:
            # 获取文件元数据
            file_metadata = await self.get_file_metadata(file_id)
            
            # 从 MinIO 下载文件并计算校验和
            file_data = await self._download_file_from_minio(file_metadata.minio_object_name)
            
            # 计算实际的 MD5 校验和
            import hashlib
            actual_md5 = hashlib.md5(file_data).hexdigest()
            
            logger.info(f"File integrity check: expected={file_metadata.checksum_md5}, actual={actual_md5}")
            
            return actual_md5  # 返回实际的校验和，而不是字符串
            
        except Exception as e:
            logger.error(f"File integrity verification failed: {e}")
            # 返回一个特殊值或抛出异常
            raise FileProcessingError("integrity_verification", str(e))

    # File management methods
    async def upload_file(self, file: UploadFile, user_id: str, tenant_id: str, metadata: Dict[str, Any]) -> File:
        """Upload file (for small files)"""
        try:
            # Read file content
            content = await file.read()
            filename = file.filename
            content_type = file.content_type or "application/octet-stream"
            
            # 提取扩展名和确定文件类型
            extension = self._get_file_extension(filename)
            file_type = self._determine_file_type(filename, extension, content_type)
            
            # 处理可见性
            visibility = FileVisibility.PRIVATE
            if 'visibility' in metadata:
                try:
                    visibility = FileVisibility(metadata['visibility'].lower())
                except ValueError:
                    visibility = FileVisibility.PRIVATE
            
            # Create file metadata
            file_metadata = File(
                filename=filename,
                file_size=len(content),
                content_type=content_type,
                extension=extension,
                file_type=file_type,
                minio_bucket=settings.MINIO_BUCKET_NAME or "foxmask",
                minio_object_name=self._generate_minio_object_name(filename),
                status=FileStatus.UPLOADED,
                uploaded_by=user_id,
                tenant_id=tenant_id,
                tags=metadata.get("tags", []),
                description=metadata.get("description"),
                visibility=visibility,
                allowed_users=metadata.get("allowed_users", []),
                allowed_roles=metadata.get("allowed_roles", []),
                metadata=metadata.get("metadata", {}),
                checksum_md5=calculate_md5_hash(content),
                uploaded_at=get_current_time()
            )
            
            # Upload to MinIO
            await self._upload_to_minio(file_metadata.minio_object_name, content)
            
            await file_metadata.insert()
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {e}"
            )

    async def _upload_to_minio(self, object_name: str, content: bytes):
        """Upload content to MinIO"""
        try:
            await self._run_in_thread(
                self.minio.upload_file,
                object_name,
                content
            )
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise

    async def get_file_metadata(self, file_id: str) -> Optional[File]:
        """Get file metadata by ID"""
        return await File.get(file_id)

    async def get_presigned_download_url(self, file_id: str, expires: int = 3600) -> Optional[str]:
        """Generate presigned download URL"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                return None
            
            return await self._run_in_thread(
                self.minio.presign_upload_part_url,
                file_metadata.minio_bucket,
                file_metadata.minio_object_name,
                expires=timedelta(seconds=expires)
            )
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from MinIO and database"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                return False
            
            # Check permissions
            if file_metadata.uploaded_by != user_id:
                raise HTTPException(status_code=403, detail="Permission denied")
            
            # Delete from MinIO
            await self._run_in_thread(
                self.minio.delete_file,
                file_metadata.minio_bucket,
                file_metadata.minio_object_name
            )
            
            # Delete from database
            await file_metadata.delete()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    async def list_user_files(self, user_id: str, skip: int = 0, limit: int = 10) -> List[File]:
        """List files uploaded by a user"""
        return await File.find(
            File.uploaded_by == user_id
        ).skip(skip).limit(limit).to_list()

    async def download_file_chunked(
        self, 
        file_id: str, 
        chunk_size: int = 5 * 1024 * 1024,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """Download file in chunks with support for resumable downloads"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                raise HTTPException(status_code=404, detail="File not found")
            
            # Generate download URLs for each chunk
            total_chunks = math.ceil(file_metadata.file_size / chunk_size)
            chunk_urls = {}
            
            for chunk_number in range(1, total_chunks + 1):
                start_byte = (chunk_number - 1) * chunk_size
                end_byte = min(chunk_number * chunk_size, file_metadata.file_size) - 1
                
                url = await self._generate_chunk_download_url(
                    file_metadata.minio_object_name,
                    start_byte,
                    end_byte
                )
                chunk_urls[chunk_number] = {
                    "url": url,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "chunk_size": end_byte - start_byte + 1
                }
            
            return {
                "filename": file_metadata.filename,
                "file_size": file_metadata.file_size,
                "content_type": file_metadata.content_type,
                "total_chunks": total_chunks,
                "chunk_size": chunk_size,
                "chunk_urls": chunk_urls,
                "checksum_md5": file_metadata.checksum_md5
            }
            
        except Exception as e:
            logger.error(f"Error preparing chunked download for file {file_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to prepare download: {e}"
            )

    async def _generate_chunk_upload_url(
        self, object_name: str, upload_id: str, chunk_number: int
    ) -> str:
        """Generate presigned URL for chunk upload"""
        try:
            return await self._run_in_thread(
                self.minio.presign_upload_part_url,
                settings.MINIO_BUCKET_NAME or "foxmask",
                object_name,
                upload_id,
                chunk_number,
                timedelta(hours=24)
            )
        except S3Error as e:
            logger.error(f"Failed to generate chunk upload URL: {e}")
            raise

    async def get_download_status(self, file_id: str) -> Dict[str, Any]:
        """Get download status and statistics"""
        file_metadata = await self.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "file_id": file_id,
            "filename": file_metadata.filename,
            "file_size": file_metadata.file_size,
            "available": True,
            "last_accessed": get_current_time().isoformat()
        }

    async def update_file_metadata(self, file_id: str, updates: Dict[str, Any], user_id: str) -> Optional[File]:
        """Update file metadata"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                return None
            
            # Check permissions
            if file_metadata.uploaded_by != user_id:
                raise HTTPException(status_code=403, detail="Permission denied")
            
            # Update allowed fields
            allowed_fields = ['tags', 'description', 'visibility', 'allowed_users', 'allowed_roles', 'metadata']
            for field in allowed_fields:
                if field in updates:
                    setattr(file_metadata, field, updates[field])
            
            file_metadata.updated_at = get_current_time()
            await file_metadata.save()
            
            return file_metadata
            
        except Exception as e:
            logger.error(f"Error updating file metadata: {e}")
            return None

    async def increment_download_count(self, file_id: str) -> None:
        """Increment file download count"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if file_metadata:
                file_metadata.increment_download_count()
                await file_metadata.save()
        except Exception as e:
            logger.error(f"Error incrementing download count: {e}")

    async def increment_view_count(self, file_id: str) -> None:
        """Increment file view count"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if file_metadata:
                file_metadata.increment_view_count()
                await file_metadata.save()
        except Exception as e:
            logger.error(f"Error incrementing view count: {e}")

    async def check_file_access(self, file_id: str, user_id: str, user_roles: List[str]) -> bool:
        """Check if user has access to file"""
        try:
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                return False
            
            return file_metadata.can_be_accessed_by(user_id, user_roles)
        except Exception as e:
            logger.error(f"Error checking file access: {e}")
            return False

file_service = FileService()