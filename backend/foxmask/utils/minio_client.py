# -*- coding: utf-8 -*-
# MinIO client utility

from minio import Minio, datatypes
from minio.error import S3Error
from typing import Optional, BinaryIO, Any, Dict, List, Union
from io import BytesIO
from datetime import timedelta, timezone, datetime
from foxmask.core.config import settings
from foxmask.core.logger import logger
import os
import mimetypes
import asyncio

class MinIOClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY.get_secret_value() if hasattr(settings.MINIO_ACCESS_KEY, "get_secret_value") else settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY.get_secret_value() if hasattr(settings.MINIO_SECRET_KEY, "get_secret_value") else settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        # self.bucket_name = settings.MINIO_BUCKET_NAME
        self.bucket_name = getattr(settings, 'MINIO_BUCKET_NAME', 'foxmask')
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists"""
        try:
            if not self.bucket_exists(self.bucket_name):
                self.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists"""
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            logger.error(f"Error checking bucket existence: {e}")
            return False

    def make_bucket(self, bucket_name: str) -> bool:
        """Create a bucket"""
        try:
            self.client.make_bucket(bucket_name)
            logger.info(f"Bucket created: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            return False

    # 同步方法
    def put_object(
        self, 
        bucket_name: str, 
        object_name: str, 
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """上传对象到 MinIO - 兼容服务层接口"""
        try:
            # 确保桶存在
            if not self.bucket_exists(bucket_name):
                self.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            
            # 将 bytes 转换为 BytesIO
            data_stream = BytesIO(data)
            
            # 准备额外的 headers
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type
            if metadata:
                # 将 metadata 字典转换为 MinIO 的 headers 格式
                for key, value in metadata.items():
                    headers[f"X-Amz-Meta-{key}"] = str(value)
            
            # 上传对象
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(data),
                content_type=content_type,
                metadata=metadata
            )
            
            logger.info(f"Successfully uploaded object: {object_name} to bucket: {bucket_name}")
            
            return {
                "success": True,
                "etag": result.etag,
                "version_id": getattr(result, 'version_id', None),
                "bucket": bucket_name,
                "object": object_name
            }
            
        except S3Error as e:
            logger.error(f"MinIO upload failed - Bucket: {bucket_name}, Object: {object_name}, Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "bucket": bucket_name,
                "object": object_name
            }
        except Exception as e:
            logger.error(f"Unexpected error during MinIO upload: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "bucket": bucket_name,
                "object": object_name
            }

    def upload_file(
        self, 
        object_name: str, 
        file_data: Union[BinaryIO, bytes],
        content_type: str = "application/octet-stream",
        bucket_name: str = None
    ) -> Dict[str, Any]:
        """Upload file to MinIO - 返回字典格式"""
        try:
            if bucket_name is None:
                bucket_name = self.bucket_name
                
            # 处理bytes类型数据
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)
            
            # Reset file pointer to beginning
            file_data.seek(0)
            
            # 获取数据长度
            if hasattr(file_data, 'getbuffer'):
                length = len(file_data.getbuffer())
            else:
                # 对于普通文件对象，需要先保存当前位置
                current_pos = file_data.tell()
                file_data.seek(0, 2)  # 移动到文件末尾
                length = file_data.tell()
                file_data.seek(current_pos)  # 恢复位置
            
            result = self.client.put_object(
                bucket_name,
                object_name,
                file_data,
                length=length,
                content_type=content_type
            )
            
            logger.info(f"File uploaded successfully: {object_name}")
            
            return {
                "success": True,
                "etag": result.etag,
                "version_id": getattr(result, 'version_id', None),
                "bucket": bucket_name,
                "object": object_name
            }
            
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            return {
                "success": False,
                "error": str(e),
                "bucket": bucket_name,
                "object": object_name
            }
        except Exception as e:
            logger.error(f"Unexpected upload error: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "bucket": bucket_name,
                "object": object_name
            }

    # 异步方法包装器
    async def put_object_async(
        self, 
        bucket_name: str, 
        object_name: str, 
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """异步版本的 put_object - 添加调试"""
        try:
            logger.info(f"=== MINIO CLIENT UPLOAD DEBUG ===")
            logger.info(f"Bucket: {bucket_name}")
            logger.info(f"Object: {object_name}")
            logger.info(f"Data size: {len(data)} bytes")
            logger.info(f"Content type: {content_type}")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.put_object, 
                bucket_name, object_name, data, content_type, metadata
            )
            
            logger.info(f"MinIO client result: {result}")
            logger.info(f"=== END CLIENT DEBUG ===")
            
            # ✅ 确保返回正确的格式
            if isinstance(result, dict) and "etag" in result:
                return result["etag"]
            else:
                return "unknown-etag"
                
        except Exception as e:
            logger.error(f"MinIO client upload failed: {e}", exc_info=True)
            raise
        
    async def upload_file_async(
        self, 
        object_name: str, 
        file_data: Union[BinaryIO, bytes],
        content_type: str = "application/octet-stream",
        bucket_name: str = None
    ) -> Dict[str, Any]:
        """异步版本的 upload_file"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.upload_file, 
            object_name, file_data, content_type, bucket_name
        )
    
    async def download_file(self, bucket_name: str, object_name: str, file_path: str) -> bool:
        """从MinIO下载文件到本地路径"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self.client.fget_object, 
                bucket_name, object_name, file_path
            )
            logger.info(f"File downloaded successfully: {bucket_name}/{object_name} -> {file_path}")
            return True
        except S3Error as e:
            logger.error(f"MinIO download error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected download error: {e}")
            return False
    
    async def download_file_as_bytes(self, object_name: str, bucket_name: str = None) -> Optional[bytes]:
        """下载文件并返回字节数据"""
        if bucket_name is None:
            bucket_name = self.bucket_name
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.client.get_object,
                bucket_name, object_name
            )
            
            file_data = response.read()
            
            # 正确关闭响应
            response.close()
            response.release_conn()
            
            logger.info(f"File downloaded as bytes successfully: {bucket_name}/{object_name}")
            return file_data
            
        except S3Error as e:
            logger.error(f"MinIO download error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected download error: {e}")
            return None
        
    def get_presigned_url(
        self, 
        object_name: str, 
        bucket_name: str = None,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """Generate presigned URL for file access"""
        try:
            if bucket_name is None:
                bucket_name = self.bucket_name
                
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned URL error: {e}")
            return None

    def get_presigned_put_url(
        self, 
        object_name: str, 
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """Generate presigned URL for file upload"""
        try:
            url = self.client.presigned_put_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned upload URL error: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def list_files(self, prefix: str = "", recursive: bool = False) -> list:
        """List files in bucket"""
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"MinIO list objects error: {e}")
            return []

    def get_file_info(self, object_name: str) -> Optional[dict]:
        """Get file metadata"""
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag
            }
        except S3Error as e:
            logger.error(f"MinIO stat error: {e}")
            return None

    def create_multipart_upload(self, bucket_name: str, object_name: str, content_type: str = "application/octet-stream") -> str:
        """Create multipart upload"""
        try:
            return self.client._create_multipart_upload(
                bucket_name,
                object_name,
                headers={"Content-Type": content_type}
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload creation failed: {e}")
            raise

    def upload_part(
        self, 
        bucket_name: str,
        object_name: str, 
        upload_id: str, 
        part_number: int, 
        data: bytes,
        checksum: Optional[str] = None
    ) -> str:
        """Upload a part"""
        try:
            if hasattr(data, 'read'):
                # 如果是 BytesIO 或其他文件类对象，读取内容
                data = data.read()

            result = self.client._upload_part(
                bucket_name=bucket_name,
                object_name=object_name,
                upload_id=upload_id,
                part_number=part_number,
                data=data,
                headers=None
             )
            return result
        except S3Error as e:
            logger.error(f"MinIO part upload failed: {e}")
            raise

    def complete_multipart_upload(
        self, bucket_name: str, object_name: str, upload_id: str, parts: List[Dict[str, Any]]
    ) -> None:
        print(f"MINIO complete_multipart_upload Call: start:{str(parts)}")
        """Complete multipart upload"""
        try:
            # 直接使用字典格式，确保键名正确
            formatted_parts: List[datatypes.Part] = []  # 正确类型注释

            for part in parts:
                # 获取 part_number 和 etag
                part_number = part.get("PartNumber") or part.get("partNumber") or part.get("part_number")
                etag = part.get("etag") or part.get("ETag") or part.get("Etag")
                
                # 确保值不为 None
                if part_number is None:
                    raise ValueError(f"Missing part_number in part: {part}")
                if etag is None:
                    raise ValueError(f"Missing etag in part: {part}")
                
                # 创建 Part 对象
                part_obj = datatypes.Part(
                    part_number=int(part_number),  # 确保是整数
                    etag=str(etag),               # 确保是字符串
                    last_modified=None,           # 可选参数
                    size=None                     # 可选参数
                )
                
                formatted_parts.append(part_obj)
           
            self.client._complete_multipart_upload(
                bucket_name,
                object_name,
                upload_id,
                formatted_parts
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload completion failed: {e}")
            raise

    def abort_multipart_upload(self, bucket_name: str, object_name: str, upload_id: str) -> None:
        """Abort multipart upload"""
        try:
            self.client._abort_multipart_upload(
                bucket_name,
                object_name,
                upload_id
            )
        except S3Error as e:
            logger.error(f"MinIO multipart upload abortion failed: {e}")
            raise

    def list_parts(self, bucket_name: str, object_name: str, upload_id: str) -> List[Dict[str, Any]]:
        """List parts of a multipart upload"""
        try:
            parts = self.client._list_parts(
                bucket_name,
                object_name,
                upload_id
            )
            return [{"part_number": p.part_number, "etag": p.etag} for p in parts]
        except S3Error as e:
            logger.error(f"MinIO list parts failed: {e}")
            return []

    def presign_upload_part_url(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
        part_number: int,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """Generate presigned URL for upload part"""
        try:
            # 使用 _presigned_url 内部方法（如果可用）
            # 或者使用 requests 来手动构建
            
            import requests
            from datetime import datetime
            
            # 获取当前时间
            now = datetime.now(timezone.utc)
            expiry_time = now + expires
        
            # 最简单的解决方案：使用普通的PUT预签名URL，然后在客户端添加查询参数
            base_url = self.client.presigned_put_object(
                bucket_name,
                object_name,
                expires=expires
            )
            
            # 添加分块上传参数
            if '?' in base_url:
                return f"{base_url}&partNumber={part_number}&uploadId={upload_id}"
            else:
                return f"{base_url}?partNumber={part_number}&uploadId={upload_id}"
                
        except S3Error as e:
            logger.error(f"MinIO upload part presigned URL generation failed: {e}")
            return None

    def upload_directory(self,bucket_name, local_dir, prefix=""):
        """
        将 local_dir 下的所有文件递归上传到 bucket，
        相对路径被用作对象名（并替换为 '/'），
        prefix 可用于给对象名前加一个前缀路径（可为空）。
        """
        uploaded = []
        local_dir = os.path.abspath(local_dir)
        for root, dirs, files in os.walk(local_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, local_dir)
                # 统一用 '/' 作为对象路径分隔符
                object_name = os.path.join(prefix, rel_path).replace(os.sep, "/").lstrip("/")
                content_type, _ = mimetypes.guess_type(full_path)
                if content_type is None:
                    content_type = "application/octet-stream"
                try:
                    self.client.fput_object(bucket_name, object_name, full_path, content_type=content_type)
                    uploaded.append(object_name)
                    print(f"Uploaded: {object_name}")
                except S3Error as e:
                    print(f"Failed to upload {full_path}: {e}")
        return uploaded    
    
    def get_object(self, bucket_name: str, object_name: str) -> Any:
        """获取对象 - 同步版本"""
        try:
            return self.client.get_object(bucket_name, object_name)
        except S3Error as e:
            logger.error(f"MinIO get object failed - Bucket: {bucket_name}, Object: {object_name}, Error: {e}")
            raise
    
    def stat_object(self, bucket_name: str, object_name: str) -> Any:
        """获取对象状态 - 同步版本"""
        try:
            return self.client.stat_object(bucket_name, object_name)
        except S3Error as e:
            logger.error(f"MinIO stat object failed - Bucket: {bucket_name}, Object: {object_name}, Error: {e}")
            raise
    
    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """删除对象 - 同步版本"""
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as e:
            logger.error(f"MinIO remove object failed - Bucket: {bucket_name}, Object: {object_name}, Error: {e}")
            raise
    
    def copy_object(self, bucket_name: str, object_name: str, copy_source: Any, **kwargs) -> Any:
        """复制对象 - 同步版本"""
        try:
            return self.client.copy_object(bucket_name, object_name, copy_source, **kwargs)
        except S3Error as e:
            logger.error(f"MinIO copy object failed - Bucket: {bucket_name}, Object: {object_name}, Error: {e}")
            raise
    
    def CopySource(self, bucket_name: str, object_name: str) -> Any:
        """创建复制源 - 同步版本"""
        try:
            # 根据你的 MinIO 客户端库调整
            # 对于 minio-py，可能是这样的：
            from minio.commonconfig import CopySource
            return CopySource(bucket_name, object_name)
        except Exception as e:
            logger.error(f"MinIO CopySource creation failed: {e}")
            raise

# Global MinIO client instance
minio_client = MinIOClient()