# -*- coding: utf-8 -*-
# foxmask/file/repositories/minio_repository.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# MinIO repository for storage operations

# 标准库导入
import asyncio
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

# 本地模块导入
from foxmask.core.config import settings
from foxmask.core.exceptions import ExternalServiceError
from foxmask.core.logger import logger
from foxmask.file.models import File
from foxmask.utils.helpers import generate_uuid
from foxmask.utils.minio_client import minio_client


class MinIORepository:
    """MinIO存储仓库类 - 处理MinIO存储操作"""
    
    def __init__(self):
        """初始化MinIO客户端和线程池"""
        self.minio = minio_client
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _run_in_thread(self, func, *args, **kwargs) -> Any:
        """
        在线程池中运行同步MinIO操作
        
        Args:
            func: MinIO同步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def _get_tenant_bucket_name(self, tenant_id: str) -> str:
        """
        获取租户对应的存储桶名称
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            str: 存储桶名称
        """
        if not settings.MINIO_USE_TENANT_BUCKETS:
            return settings.MINIO_DEFAULT_BUCKET
        
        # 清理租户ID，确保符合存储桶命名规范
        clean_tenant_id = tenant_id.replace('_', '-').lower()
        bucket_name = f"{settings.MINIO_BUCKET_PREFIX}-{clean_tenant_id}"
        
        # 确保存储桶存在
        await self._ensure_bucket_exists(bucket_name)
        return bucket_name
    
    async def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        确保存储桶存在
        
        Args:
            bucket_name: 存储桶名称
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
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
        """
        从文件信息获取存储桶名称
        
        Args:
            file_id: 文件ID
            
        Returns:
            str: 存储桶名称
        """
        try:
            file = await File.get(file_id)
            if file:
                return file.minio_bucket
            return settings.MINIO_DEFAULT_BUCKET
        except Exception:
            logger.warning(f"Failed to get bucket name from file {file_id}, using default")
            return settings.MINIO_DEFAULT_BUCKET
    
    async def _generate_object_name(self, tenant_id: str, user_id: str, filename: str) -> str:
        """
        生成MinIO对象名称
        
        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            filename: 原始文件名
            
        Returns:
            str: 对象名称
        """
        from datetime import datetime
        
        now = datetime.now()
        extension = self._get_file_extension(filename)
        unique_id = generate_uuid()[:8]
        
        if settings.FILE_STORAGE_PATH_FORMAT:
            object_name = settings.FILE_STORAGE_PATH_FORMAT.format(
                tenant_id=tenant_id,
                user_id=user_id,
                year=now.year,
                month=f"{now.month:02d}",
                day=f"{now.day:02d}",
                filename=f"{int(now.timestamp())}_{unique_id}.{extension}" if extension else f"{int(now.timestamp())}_{unique_id}"
            )
        else:
            object_name = f"{tenant_id}/{now.year}/{now.month:02d}/{now.day:02d}/{int(now.timestamp())}_{unique_id}"
            if extension:
                object_name += f".{extension}"
        
        logger.debug(f"Generated object name: {object_name}")
        return object_name
    
    def _get_file_extension(self, filename: str) -> str:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            str: 文件扩展名
        """
        if not filename or '.' not in filename:
            return ''
        
        parts = filename.rsplit('.', 2)
        if len(parts) > 2 and parts[-2].lower() == 'tar':
            return 'tar.gz'
        return parts[-1].lower()
    
    async def initiate_multipart_upload(self, tenant_id: str, object_name: str) -> str:
        """
        初始化多部分上传
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            
        Returns:
            str: 上传ID
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            upload_id = await self._run_in_thread(
                self.minio.create_multipart_upload,
                bucket_name,
                object_name
            )
            logger.info(f"Multipart upload initiated: {upload_id}")
            return upload_id
        except Exception as e:
            logger.error(f"MinIO multipart upload initiation failed: {e}")
            raise ExternalServiceError("MinIO", "initiate_multipart_upload", str(e))
    
    async def generate_chunk_upload_url(
        self, tenant_id: str, object_name: str, upload_id: str, chunk_number: int, expires: timedelta
    ) -> str:
        """
        生成分片上传URL
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            upload_id: 上传ID
            chunk_number: 分片编号
            expires: 过期时间
            
        Returns:
            str: 预签名URL
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        logger.debug(f"Generating chunk upload URL for tenant: {tenant_id}, object: {object_name}")
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        
        try:
            url = await self._run_in_thread(
                self.minio.presign_upload_part_url,
                bucket_name,
                object_name=object_name,
                upload_id=upload_id,
                part_number=chunk_number,
                expires=expires
            )
            logger.debug(f"Generated upload URL for chunk {chunk_number}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate chunk upload URL: {e}")
            raise ExternalServiceError("MinIO", "generate_upload_url", str(e))
    
    async def upload_chunk(
        self, tenant_id: str, object_name: str, upload_id: str, chunk_number: int, chunk_data: bytes, checksum_md5: Optional[str] = None
    ) -> str:
        """
        上传文件分片
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            upload_id: 上传ID
            chunk_number: 分片编号
            chunk_data: 分片数据
            checksum_md5: MD5校验和
            
        Returns:
            str: ETag标识
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            etag = await self._run_in_thread(
                self.minio.upload_part,
                bucket_name,
                object_name,
                upload_id,
                chunk_number,
                chunk_data,
                checksum_md5
            )
            logger.info(f"Chunk uploaded successfully: {chunk_number}, ETag: {etag}")
            return etag
        except Exception as e:
            logger.error(f"MinIO chunk upload failed: {e}")
            raise ExternalServiceError("MinIO", "upload_chunk", str(e))
    
    async def complete_multipart_upload(
        self, tenant_id: str, object_name: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> None:
        """
        完成多部分上传
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            upload_id: 上传ID
            parts: 分片信息列表
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.complete_multipart_upload,
                bucket_name,
                object_name,
                upload_id,
                parts
            )
            logger.info(f"Multipart upload completed: {upload_id}")
        except Exception as e:
            logger.error(f"MinIO multipart upload completion failed: {e}")
            raise ExternalServiceError("MinIO", "complete_multipart_upload", str(e))
    
    async def abort_multipart_upload(self, tenant_id: str, object_name: str, upload_id: str) -> None:
        """
        中止多部分上传
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            upload_id: 上传ID
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.abort_multipart_upload,
                bucket_name,
                object_name,
                upload_id
            )
            logger.info(f"Multipart upload aborted: {upload_id}")
        except Exception as e:
            logger.error(f"MinIO multipart upload abortion failed: {e}")
            raise ExternalServiceError("MinIO", "abort_multipart_upload", str(e))
    
    async def upload_file(self, tenant_id: str, object_name: str, content: bytes) -> None:
        """
        上传完整文件
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            content: 文件内容
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.upload_file,
                bucket_name,
                object_name,
                content
            )
            logger.info(f"File uploaded successfully: {object_name}")
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise ExternalServiceError("MinIO", "upload_file", str(e))
    
    async def download_file(self, tenant_id: str, object_name: str) -> bytes:
        """
        下载文件
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            
        Returns:
            bytes: 文件内容
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            content = await self._run_in_thread(
                self.minio.download_file,
                bucket_name,
                object_name
            )
            logger.info(f"File downloaded successfully: {object_name}")
            return content
        except Exception as e:
            logger.error(f"MinIO download failed: {e}")
            raise ExternalServiceError("MinIO", "download_file", str(e))
    
    async def delete_file(self, tenant_id: str, object_name: str) -> None:
        """
        删除文件
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.delete_object,
                bucket_name,
                object_name
            )
            logger.info(f"File deleted successfully: {object_name}")
        except Exception as e:
            logger.error(f"MinIO delete failed: {e}")
            raise ExternalServiceError("MinIO", "delete_file", str(e))
    
    async def generate_download_url(self, tenant_id: str, object_name: str, expires: timedelta) -> str:
        """
        生成下载URL
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            expires: 过期时间
            
        Returns:
            str: 预签名URL
            
        Raises:
            ExternalServiceError: MinIO操作失败时抛出
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            url = await self._run_in_thread(
                self.minio.presign_get_object,
                bucket_name,
                object_name,
                expires=expires
            )
            logger.debug(f"Generated download URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise ExternalServiceError("MinIO", "generate_download_url", str(e))
    
    async def file_exists(self, tenant_id: str, object_name: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            tenant_id: 租户ID
            object_name: 对象名称
            
        Returns:
            bool: 文件是否存在
        """
        bucket_name = await self._get_tenant_bucket_name(tenant_id)
        try:
            await self._run_in_thread(
                self.minio.stat_object,
                bucket_name,
                object_name
            )
            logger.debug(f"File exists: {object_name}")
            return True
        except Exception:
            logger.debug(f"File not found: {object_name}")
            return False


# 全局MinIO仓库实例
minio_repository = MinIORepository()