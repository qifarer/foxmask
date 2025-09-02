from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, UploadFile
from typing import Optional
import io
import hashlib

from foxmask.core.minio import minio_client
from foxmask.core.config import get_settings

settings = get_settings()

class MinioService:
    def __init__(self):
        self.client = minio_client
        self.bucket = settings.MINIO_BUCKET

    async def upload_file_stream(
        self,
        file: UploadFile,
        object_name: str
    ) -> str:
        """流式上传文件到 MinIO"""
        try:
            # 确保文件指针在开头
            file.file.seek(0)

            # 获取文件大小
            file.file.seek(0, 2)  # 移动到末尾
            file_size = file.file.tell()
            file.file.seek(0)     # 回到开头

            # 上传文件流
            self.client.put_object(
                self.bucket,
                object_name,
                file.file,  # 直接传递 file-like 对象
                file_size,
                content_type=file.content_type,
            )

            # 生成预签名下载链接
            url = self.client.presigned_get_object(self.bucket, object_name)
            return url

        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"MinIO upload failed: {str(e)}")
        finally:
            try:
                file.file.seek(0)
            except:
                pass

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """上传文件到 MinIO（字节流方式）"""
        try:
            data = io.BytesIO(file_data)
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                len(file_data),
                content_type=content_type
            )
            return self.client.presigned_get_object(self.bucket, object_name)
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"MinIO upload failed: {str(e)}")

    async def calculate_file_hash_streaming(self, file: UploadFile) -> str:
        """流式计算文件哈希（支持大文件）"""
        hash_sha256 = hashlib.sha256()
        
        # 确保文件指针在开头
        await file.seek(0)
        
        # 分块读取文件计算哈希
        chunk_size = 8192  # 8KB chunks
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            hash_sha256.update(chunk)
        
        # 重置文件指针
        await file.seek(0)
        return hash_sha256.hexdigest()

    async def get_file_size(self, file: UploadFile) -> int:
        """获取文件大小"""
        current_pos = await file.tell()
        await file.seek(0, 2)  # 移动到文件末尾
        file_size = await file.tell()
        await file.seek(current_pos)  # 回到原来的位置
        return file_size

    async def get_presigned_put_url(
        self,
        object_name: str,
        expires: int = 3600
    ) -> str:
        """生成预签名上传 URL"""
        try:
            return self.client.presigned_put_object(self.bucket, object_name, expires=expires)
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")

    async def get_presigned_get_url(
        self,
        object_name: str,
        expires: int = 3600
    ) -> str:
        """生成预签名下载 URL"""
        try:
            return self.client.presigned_get_object(self.bucket, object_name, expires=expires)
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")

    async def delete_file(self, object_name: str) -> bool:
        """删除 MinIO 中的文件"""
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
        
minio_service = MinioService()