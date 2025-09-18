# -*- coding: utf-8 -*-
# foxmask/file/services.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# File service for business logic

import asyncio
import math, json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import UploadFile

from foxmask.core.config import settings
from foxmask.core.exceptions import (
    ExternalServiceError,
    FileProcessingError,
    NotFoundError,
    ValidationError,
)
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.task.message.schemas import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    MessagePriorityEnum
)
from foxmask.file.models import (
    EXTENSION_FILE_TYPES,
    ChunkStatus,
    File,
    FileChunk,
    FileStatus,
    FileType,
    FileVisibility,
)
from foxmask.file.repositories import file_repository, minio_repository
from foxmask.utils.helpers import calculate_md5_hash, generate_uuid, get_current_time


class FileService:
    """文件服务类，处理文件上传、下载、管理等业务逻辑"""

    def __init__(self):
        self.chunk_size = 5 * 1024 * 1024  # 5MB
        self.settings = settings

    def _determine_file_type(self, filename: str, content_type: str) -> FileType:
        """
        根据文件名和内容类型确定文件类型
        
        Args:
            filename: 文件名
            content_type: 内容类型
            
        Returns:
            FileType: 文件类型枚举值
        """
        extension = self._get_file_extension(filename)
        
        # 首先根据文件扩展名判断
        if extension and f".{extension}" in EXTENSION_FILE_TYPES:
            return EXTENSION_FILE_TYPES[f".{extension}"]
        
        # 根据内容类型判断
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
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            str: 文件扩展名（小写），如 'txt', 'jpg' 等
        """
        if not filename or '.' not in filename:
            return ''
        
        parts = filename.rsplit('.', 2)
        # 处理特殊扩展名如 .tar.gz
        if len(parts) > 2 and parts[-2].lower() == 'tar':
            return 'tar.gz'
        return parts[-1].lower()
    
    async def create_file(self, file_data: Dict[str, Any], user_id: str, tenant_id: str) -> File:
        """
        创建文件元数据记录
        
        Args:
            file_data: 文件数据字典
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            File: 文件对象
            
        Raises:
            FileProcessingError: 创建文件元数据时出错
        """
        try:
            filename = file_data.get('filename')
            file_size = file_data.get('file_size')
            content_type = file_data.get('content_type', "application/octet-stream")
            
            extension = self._get_file_extension(filename)
            file_type = self._determine_file_type(filename, content_type)
            
            minio_object_name = await minio_repository._generate_object_name(tenant_id, user_id, filename)
            minio_bucket = await minio_repository._get_tenant_bucket_name(tenant_id)
            
            # 处理文件可见性设置
            visibility = FileVisibility.PRIVATE
            if 'visibility' in file_data and file_data.get('visibility'):
                try:
                    visibility = FileVisibility(file_data.get('visibility'))
                except ValueError:
                    visibility = FileVisibility.PRIVATE
            
            # 构建文件参数
            file_kwargs = {
                'filename': filename,
                'file_size': file_size,
                'content_type': content_type,
                'extension': extension,
                'file_type': file_type,
                'minio_object_name': minio_object_name,
                'minio_bucket': minio_bucket,
                'uploaded_by': user_id,
                'tenant_id': tenant_id,
                'status': FileStatus.DRAFT,
                'upload_progress': 0.0,
                'visibility': visibility,
                'allowed_users': file_data.get('allowed_users', []),
                'allowed_roles': file_data.get('allowed_roles', []),
                'tags': file_data.get('tags', []),
                'description': file_data.get('description'),
                'metadata': file_data.get('metadata', {}),
                'is_multipart': file_data.get('is_multipart', False),
                'chunk_size': file_data.get('chunk_size', self.chunk_size),
                'total_chunks': 0,
                'uploaded_chunks': 0,
                'verified_chunks': 0
            }
            
            # 过滤掉None值
            file_kwargs = {k: v for k, v in file_kwargs.items() if v is not None}
            
            return await file_repository.create_file(file_kwargs)
            
        except Exception as e:
            logger.error(f"Error creating file metadata: {e}")
            raise FileProcessingError("create_file", str(e))
    
    async def init_multipart_upload(self, file_data: Dict[str, Any], user_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        初始化分片上传
        
        Args:
            file_data: 文件数据字典
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            Dict: 包含上传ID、分片URL等信息的字典
            
        Raises:
            FileProcessingError: 初始化分片上传时出错
        """
        logger.debug(f"Initializing multipart upload for file: {file_data.get('filename')}")
        
        try:
            filename = file_data.get('filename')
            file_size = file_data.get('file_size')
            content_type = file_data.get('content_type', "application/octet-stream")
            chunk_size = file_data.get('chunk_size', self.chunk_size)
            
            total_chunks = math.ceil(file_size / chunk_size)
            
            # 创建文件记录
            file = await self.create_file(file_data, user_id, tenant_id)
            minio_object_name = file.minio_object_name
            
            # 初始化MinIO分片上传
            upload_id = await minio_repository.initiate_multipart_upload(
                tenant_id, minio_object_name
            )
            
            # 更新文件记录
            await file_repository.update_file(str(file.id), {
                'upload_id': upload_id,
                'status': FileStatus.UPLOADING,
                'total_chunks': total_chunks,
                'updated_at': get_current_time()
            })
            
            # 创建分片记录
            await self._create_chunk_records(str(file.id), upload_id, total_chunks, chunk_size, file_size)
            
            # 生成分片上传URL
            chunk_urls = {}
            for chunk_number in range(1, total_chunks + 1):
                url = await minio_repository.generate_chunk_upload_url(
                    tenant_id,
                    minio_object_name,
                    upload_id,
                    chunk_number,
                    timedelta(hours=24)
                )
                chunk_urls[chunk_number] = url

            logger.info(f"Multipart upload initialized for file {file.id}, total chunks: {total_chunks}")
            
            return {
                "file_id": str(file.id),
                "upload_id": upload_id,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "chunk_urls": chunk_urls,
                "minio_bucket": file.minio_bucket
            }
        
        except Exception as e:
            logger.error(f"Error initializing multipart upload: {e}")
            raise FileProcessingError("init_multipart_upload", str(e))
    
    async def _create_chunk_records(
        self,
        file_id: str,
        upload_id: str,
        total_chunks: int,
        chunk_size: int,
        file_size: int
    ) -> None:
        """
        创建分片记录
        
        Args:
            file_id: 文件ID
            upload_id: 上传ID
            total_chunks: 总分片数
            chunk_size: 分片大小
            file_size: 文件总大小
            
        Raises:
            FileProcessingError: 创建分片记录时出错
        """
        logger.debug(f"Creating chunk records for file {file_id}, total chunks: {total_chunks}")
        
        chunks: List[FileChunk] = []
        bucket_name = await minio_repository._get_tenant_bucket_name_from_file(file_id)

        for chunk_number in range(1, total_chunks + 1):
            start_byte = (chunk_number - 1) * chunk_size
            end_byte = min(start_byte + chunk_size, file_size) - 1

            # 创建FileChunk实例
            chunk = FileChunk(
                file_id=file_id,
                upload_id=upload_id,
                chunk_number=chunk_number,
                chunk_size=chunk_size,
                start_byte=start_byte,
                end_byte=end_byte,
                minio_object_name=f"chunks/{upload_id}/part-{chunk_number}",
                minio_bucket=bucket_name,
                status=ChunkStatus.PENDING,
            )
            chunks.append(chunk)

        try:
            await file_repository.create_chunks(chunks)
            logger.debug(f"Created {len(chunks)} chunk records for file {file_id}")
        except Exception as e:
            logger.error(f"Error creating chunk records: {e}")
            raise FileProcessingError("create_chunk_records", str(e))

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
        """
        上传文件分片
        
        Args:
            file_id: 文件ID
            upload_id: 上传ID
            chunk_number: 分片编号
            chunk_data: 分片数据
            chunk_size: 分片大小
            checksum_md5: MD5校验和（可选）
            checksum_sha256: SHA256校验和（可选）
            
        Returns:
            Dict: 包含分片上传结果的字典
            
        Raises:
            ValidationError: 分片大小不匹配或分片编号无效
            NotFoundError: 文件未找到或上传ID无效
            FileProcessingError: 分片上传过程中出错
        """
        try:
            # 验证分片大小
            actual_size = len(chunk_data)
            if chunk_size != actual_size:
                raise ValidationError(
                    f"Chunk size mismatch: expected {chunk_size}, got {actual_size}",
                    {"expected_size": chunk_size, "actual_size": actual_size}
                )
            
            # 获取文件记录
            file = await file_repository.get_file_by_id(file_id)
            if not file or file.upload_id != upload_id:
                raise NotFoundError("File", file_id, "File not found or invalid upload ID")
            
            # 验证分片编号
            if chunk_number < 1 or chunk_number > file.total_chunks:
                raise ValidationError(
                    f"Invalid chunk number: {chunk_number}. Must be between 1 and {file.total_chunks}",
                    {"chunk_number": chunk_number, "total_chunks": file.total_chunks}
                )
            
            # 计算MD5校验和（如果未提供）
            if not checksum_md5:
                checksum_md5 = calculate_md5_hash(chunk_data)
            
            # 上传分片到MinIO
            etag = await minio_repository.upload_chunk(
                file.tenant_id,
                file.minio_object_name,
                upload_id,
                chunk_number,
                chunk_data,
                checksum_md5
            )
            
            # 更新分片记录
            chunk = await file_repository.get_chunk(file_id, chunk_number)
            if chunk:
                chunk.mark_uploaded(etag, get_current_time())
                chunk.checksum_md5 = checksum_md5
                chunk.checksum_sha256 = checksum_sha256
                await file_repository.update_chunk(chunk)
                
                # 更新文件上传进度
                uploaded_chunks = await file_repository.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
                verified_chunks = await file_repository.count_chunks_by_status(file_id, ChunkStatus.VERIFIED)
                
                file.uploaded_chunks = uploaded_chunks
                file.verified_chunks = verified_chunks
                
                if file.total_chunks > 0:
                    file.upload_progress = (uploaded_chunks / file.total_chunks) * 100
                
                # 如果所有分片都已上传，更新文件状态
                if uploaded_chunks == file.total_chunks:
                    file.status = FileStatus.UPLOADED
                
                await file_repository.save_file(file)
            
            # 计算分片字节范围
            start_byte = (chunk_number - 1) * chunk_size
            end_byte = min(chunk_number * chunk_size, file.file_size) - 1
            
            logger.info(f"Chunk {chunk_number} uploaded for file {file_id}, ETag: {etag}")
            
            return {
                "chunk_number": chunk_number,
                "etag": etag,
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256,
                "chunk_size": chunk_size,
                "start_byte": start_byte,
                "end_byte": end_byte
            }
            
        except Exception as e:
            logger.error(f"Error uploading chunk {chunk_number} for file {file_id}: {e}")
            raise FileProcessingError("chunk_upload", str(e))
    
    async def complete_multipart_upload(
        self,
        file_id: str,
        upload_id: str,
        chunk_etags: Dict[int, str],
        checksum_md5: Optional[str] = None,
        checksum_sha256: Optional[str] = None
    ) -> File:
        """
        完成分片上传
        
        Args:
            file_id: 文件ID
            upload_id: 上传ID
            chunk_etags: 分片ETag字典
            checksum_md5: 文件MD5校验和（可选）
            checksum_sha256: 文件SHA256校验和（可选）
            
        Returns:
            File: 更新后的文件对象
            
        Raises:
            NotFoundError: 文件未找到或上传ID无效
            ValidationError: 分片不完整或缺少ETag
            FileProcessingError: 完成分片上传过程中出错
        """
        try:
            # 获取文件记录
            file = await file_repository.get_file_by_id(file_id)
            if not file or file.upload_id != upload_id:
                raise NotFoundError("File", file_id, "File not found or invalid upload ID")
            
            # 验证所有分片是否已上传
            uploaded_chunks = await file_repository.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
            if uploaded_chunks != file.total_chunks:
                raise ValidationError(
                    f"Not all chunks uploaded. {uploaded_chunks}/{file.total_chunks} chunks ready",
                    {"uploaded_chunks": uploaded_chunks, "total_chunks": file.total_chunks}
                )
            
            # 准备分片列表用于完成上传
            parts = []
            for chunk_number in range(1, file.total_chunks + 1):
                if chunk_number not in chunk_etags:
                    raise ValidationError(f"Missing ETag for chunk {chunk_number}")
                
                chunk = await file_repository.get_chunk(file_id, chunk_number)
                if chunk and chunk.minio_etag:
                    parts.append({"PartNumber": chunk_number, "ETag": chunk.minio_etag})
                else:
                    raise ValidationError(f"Missing ETag for chunk {chunk_number}")
            
            # 按分片编号排序
            parts.sort(key=lambda x: x["PartNumber"])
            
            # 完成MinIO分片上传
            await minio_repository.complete_multipart_upload(
                file.tenant_id,
                file.minio_object_name,
                upload_id,
                parts
            )
            
            # 更新文件记录
            update_data = {
                'checksum_md5': checksum_md5,
                'checksum_sha256': checksum_sha256,
                'status': FileStatus.UPLOADED,
                'uploaded_at': get_current_time(),
                'updated_at': get_current_time()
            }
            
            file = await file_repository.update_file(file_id, update_data)
            
            if not file:
                raise NotFoundError("File", file_id, "File not found during update")
            
            # 标记所有分片为已验证
            chunks = await file_repository.get_file_chunks(file_id)
            for chunk in chunks:
                chunk.mark_verified(get_current_time())
                await file_repository.update_chunk(chunk)
            
            # 发送Kafka消息 - 文件上传完成
            
            try:
                biz_data = {
                    "type": MessageEventTypeEnum.CREATE_ITEM_FROM_FILE,
                    "file_id": file_id,
                    "tenant": file.tenant_id,
                    "user": file.uploaded_by,
                    "filename": file.filename,
                    "priority": MessagePriorityEnum.NORMAL
                }
                await kafka_manager.send_message(
                    topic=MessageTopicEnum.KB_PROCESSING,
                    value=biz_data,
                    key=file_id
                )                                            
            except Exception as kafka_error:
                # Kafka发送失败不应该影响主流程，但需要记录日志
                logger.error(f"Failed to send Kafka message for file {file_id}: {kafka_error}")
            
            logger.info(f"Multipart upload completed for file {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error completing multipart upload for file {file_id}: {e}")
            raise FileProcessingError("complete_multipart_upload", str(e))
        
    async def get_upload_progress(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件上传进度
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict: 包含上传进度信息的字典
        """
        return await file_repository.get_upload_progress(file_id)
    
    async def resume_multipart_upload(self, file_id: str) -> Dict[str, Any]:
        """
        恢复中断的分片上传
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict: 包含缺失分片和上传URL的字典
            
        Raises:
            NotFoundError: 文件未找到或不是分片上传
        """
        file = await file_repository.get_file_by_id(file_id)
        if not file or not file.upload_id:
            raise NotFoundError("File", file_id, "File not found or not a multipart upload")
        
        # 获取已上传的分片
        uploaded_chunks = await file_repository.get_file_chunks(file_id)
        uploaded_chunk_numbers = {chunk.chunk_number for chunk in uploaded_chunks 
                                if chunk.status in [ChunkStatus.UPLOADED, ChunkStatus.VERIFIED]}
        
        # 计算缺失的分片
        all_chunk_numbers = set(range(1, file.total_chunks + 1))
        missing_chunks = sorted(all_chunk_numbers - uploaded_chunk_numbers)
        
        # 为缺失的分片生成上传URL
        chunk_urls = {}
        for chunk_number in missing_chunks:
            url = await minio_repository.generate_chunk_upload_url(
                file.tenant_id,
                file.minio_object_name,
                file.upload_id,
                chunk_number,
                timedelta(hours=24)
            )
            chunk_urls[chunk_number] = url
        
        logger.info(f"Resumed multipart upload for file {file_id}, missing chunks: {len(missing_chunks)}")
        
        return {
            "file_id": file_id,
            "upload_id": file.upload_id,
            "missing_chunks": missing_chunks,
            "chunk_urls": chunk_urls
        }
    
    async def abort_multipart_upload(self, file_id: str) -> bool:
        """
        中止分片上传
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否成功中止
            
        Raises:
            NotFoundError: 文件未找到或不是分片上传
        """
        file = await file_repository.get_file_by_id(file_id)
        if not file or not file.upload_id:
            raise NotFoundError("File", file_id, "File not found or not a multipart upload")
        
        try:
            # 中止MinIO分片上传
            await minio_repository.abort_multipart_upload(
                file.tenant_id,
                file.minio_object_name,
                file.upload_id
            )
            
            # 删除分片记录
            await file_repository.delete_file_chunks(file_id)
            
            # 更新文件状态
            await file_repository.update_file(file_id, {
                'status': FileStatus.FAILED,
                'upload_id': None,
                'updated_at': get_current_time()
            })
            
            logger.info(f"Multipart upload aborted for file {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error aborting multipart upload for file {file_id}: {e}")
            return False
    
    async def upload_file(self, file: UploadFile, user_id: str, tenant_id: str, metadata: Dict[str, Any]) -> File:
        """
        上传单个文件（非分片方式）
        
        Args:
            file: FastAPI UploadFile对象
            user_id: 用户ID
            tenant_id: 租户ID
            metadata: 文件元数据
            
        Returns:
            File: 文件对象
            
        Raises:
            FileProcessingError: 文件上传过程中出错
        """
        try:
            # 读取文件内容
            content = await file.read()
            filename = file.filename
            content_type = file.content_type or "application/octet-stream"
            
            extension = self._get_file_extension(filename)
            file_type = self._determine_file_type(filename, content_type)
            
            # 处理文件可见性设置
            visibility = FileVisibility.PRIVATE
            if 'visibility' in metadata:
                try:
                    visibility = FileVisibility(metadata['visibility'])
                except ValueError:
                    visibility = FileVisibility.PRIVATE
            
            # 生成MinIO对象名称和桶名称
            minio_object_name = await minio_repository._generate_object_name(tenant_id, user_id, filename)
            minio_bucket = await minio_repository._get_tenant_bucket_name(tenant_id)
            
            # 准备文件数据
            file_data = {
                'filename': filename,
                'file_size': len(content),
                'content_type': content_type,
                'extension': extension,
                'file_type': file_type,
                'minio_bucket': minio_bucket,
                'minio_object_name': minio_object_name,
                'status': FileStatus.UPLOADED,
                'uploaded_by': user_id,
                'tenant_id': tenant_id,
                'tags': metadata.get("tags", []),
                'description': metadata.get("description"),
                'visibility': visibility,
                'allowed_users': metadata.get("allowed_users", []),
                'allowed_roles': metadata.get("allowed_roles", []),
                'metadata': metadata.get("metadata", {}),
                'checksum_md5': calculate_md5_hash(content),
                'uploaded_at': get_current_time(),
                'created_at': get_current_time(),
                'updated_at': get_current_time()
            }
            
            # 上传文件到MinIO
            await minio_repository.upload_file(
                tenant_id,
                minio_object_name,
                content
            )
            
            # 创建文件记录
            result = await file_repository.create_file(file_data)
            logger.info(f"File uploaded successfully: {filename}, size: {len(content)} bytes")
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename if file else 'unknown'}: {e}")
            raise FileProcessingError("upload_file", str(e))
    
    async def get_file(self, file_id: str) -> Optional[File]:
        """
        根据ID获取文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[File]: 文件对象或None
        """
        return await file_repository.get_file_by_id(file_id)
    
    async def get_presigned_download_url(self, file_id: str, expires: int = 3600) -> Optional[str]:
        """
        获取预签名的文件下载URL
        
        Args:
            file_id: 文件ID
            expires: URL过期时间（秒），默认3600秒（1小时）
            
        Returns:
            Optional[str]: 预签名URL或None
        """
        try:
            file = await self.get_file(file_id)
            if not file:
                return None
            
            return await minio_repository.generate_download_url(
                file.tenant_id,
                file.minio_object_name,
                timedelta(seconds=expires)
            )
        except Exception as e:
            logger.error(f"Error generating presigned URL for file {file_id}: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否成功删除
        """
        try:
            file = await self.get_file(file_id)
            if not file:
                return False
            
            # 从MinIO删除文件
            await minio_repository.delete_file(
                file.tenant_id,
                file.minio_object_name
            )
            
            # 删除文件记录
            await file_repository.delete_file(file_id)
            
            # 如果是分片上传，删除分片记录
            if file.is_multipart:
                await file_repository.delete_file_chunks(file_id)
            
            logger.info(f"File deleted successfully: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
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
        """
        列出文件
        
        Args:
            user_id: 用户ID（可选）
            tenant_id: 租户ID（可选）
            page: 页码，默认1
            page_size: 每页数量，默认10
            status: 文件状态（可选）
            visibility: 文件可见性（可选）
            file_type: 文件类型（可选）
            tags: 标签列表（可选）
            
        Returns:
            Tuple[List[File], int]: 文件列表和总数量
        """
        return await file_repository.list_files(
            user_id, tenant_id, page, page_size, status, visibility, file_type, tags
        )
    
    async def update_file(self, file_id: str, update_data: Dict[str, Any]) -> File:
        """
        更新文件元数据
        
        Args:
            file_id: 文件ID
            update_data: 更新数据字典
            
        Returns:
            File: 更新后的文件对象
            
        Raises:
            NotFoundError: 文件未找到
            FileProcessingError: 更新文件元数据时出错
        """
        try:
            # 定义允许更新的字段
            allowed_fields = ['tags', 'description', 'visibility', 'allowed_users', 'allowed_roles', 'metadata']
            
            # 过滤更新数据
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            filtered_data['updated_at'] = get_current_time()
            
            # 更新文件记录
            file = await file_repository.update_file(file_id, filtered_data)
            if not file:
                raise NotFoundError("File", file_id, "File not found")
            
            logger.info(f"File metadata updated: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error updating file metadata for {file_id}: {e}")
            raise FileProcessingError("update_metadata", str(e))
    
    async def get_user_files_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户文件统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 包含统计信息的字典
        """
        return await file_repository.get_user_files_stats(user_id)
    
    async def increment_download_count(self, file_id: str) -> bool:
        """
        增加文件下载次数
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否成功增加
        """
        try:
            file = await file_repository.increment_download_count(file_id)
            return file is not None
        except Exception as e:
            logger.error(f"Error incrementing download count for file {file_id}: {e}")
            return False
    
    async def increment_view_count(self, file_id: str) -> bool:
        """
        增加文件查看次数
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否成功增加
        """
        try:
            file = await file_repository.increment_view_count(file_id)
            return file is not None
        except Exception as e:
            logger.error(f"Error incrementing view count for file {file_id}: {e}")
            return False
    
    async def get_file_chunks(self, file_id: str, page: int = 1, page_size: int = 50) -> List[FileChunk]:
        """
        获取文件分片列表
        
        Args:
            file_id: 文件ID
            page: 页码，默认1
            page_size: 每页数量，默认50
            
        Returns:
            List[FileChunk]: 分片列表
        """
        return await file_repository.get_file_chunks(file_id, page, page_size)
    
    async def count_file_chunks(self, file_id: str) -> int:
        """
        统计文件分片数量
        
        Args:
            file_id: 文件ID
            
        Returns:
            int: 分片数量
        """
        return await file_repository.count_file_chunks(file_id)


# 创建全局文件服务实例
file_service = FileService()