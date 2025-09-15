# -*- coding: utf-8 -*-
# MinIO client utility

from minio import Minio, datatypes
from minio.error import S3Error
from typing import Optional, BinaryIO, Any, Dict, List, Union
from io import BytesIO
from datetime import timedelta, timezone, datetime
from foxmask.core.config import settings
from foxmask.core.logger import logger

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

    def upload_file(
        self, 
        object_name: str, 
        file_data: Union[BinaryIO, bytes],
        content_type: str = "application/octet-stream"
    ) -> bool:
        """Upload file to MinIO"""
        try:
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
            
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                length=length,
                content_type=content_type
            )
            
            logger.info(f"File uploaded successfully: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected upload error: {e}")
            return False

    def download_file(self, object_name: str) -> Optional[bytes]:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            file_data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"File downloaded successfully: {object_name}")
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
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        """Generate presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
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

# Global MinIO client instance
minio_client = MinIOClient()