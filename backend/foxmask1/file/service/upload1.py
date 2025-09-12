import base64
import time
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException, UploadFile
import hashlib

from ..services.minio import MinioService
from ..models.file import FileMetadata, UploadResponse, UploadBase64ToS3Result
from ..utils.file import generate_file_path_metadata, parse_data_uri

class UploadService:
    def __init__(self, minio_service: MinioService):
        self.minio_service = minio_service

    async def upload_file_to_minio(
        self,
        file: UploadFile,
        directory: Optional[str] = None,
        pathname: Optional[str] = None,
        skip_check_file_type: bool = False,
        on_not_supported: Optional[Callable] = None,
        on_progress: Optional[Callable] = None
    ) -> UploadResponse:
        """上传文件到 MinIO（支持大文件流式上传）"""
        # 检查文件类型
        if not skip_check_file_type and not file.content_type.startswith('image'):
            if on_not_supported:
                on_not_supported()
            return UploadResponse(success=False)
        
        # 生成文件路径
        path_metadata = generate_file_path_metadata(file.filename, directory, pathname)
        
        try:
            # 流式上传到 MinIO
            url = await self.minio_service.upload_file_stream(
                file,
                path_metadata["pathname"]
            )
            
            metadata = FileMetadata(
                date=path_metadata["date"],
                dirname=path_metadata["dirname"],
                filename=path_metadata["filename"],
                path=path_metadata["pathname"]
            )
            
            return UploadResponse(data=metadata, success=True)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def calculate_file_hash(self, file: UploadFile) -> str:
        """计算文件哈希（流式处理，支持大文件）"""
        hash_sha256 = hashlib.sha256()
        # 重置文件指针到开始
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

    async def upload_base64_to_minio(
        self,
        base64_data: str,
        filename: Optional[str] = None,
        directory: Optional[str] = None,
        pathname: Optional[str] = None
    ) -> UploadBase64ToS3Result:
        """上传 base64 数据到 MinIO"""
        # ... 保持原有代码不变

    async def get_signed_upload_url(
        self,
        filename: str,
        directory: Optional[str] = None,
        pathname: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成预签名上传 URL"""
        # ... 保持原有代码不变



# 读取文件内容
        content = await file.read()
        
        # 检查文件大小
        if len(content) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=413, detail="File too large")
        
        # 检查文件类型
        if not skip_check_file_type and not file.content_type.startswith('image'):
            if on_not_supported:
                on_not_supported()
            return UploadResponse(success=False)
        
        # 计算哈希
        file_hash = sha256_hash(content)
        
        # 生成文件路径
        path_metadata = generate_file_path_metadata(file.filename, directory, pathname)
        
        # 上传到 MinIO（模拟进度回调）
        try:
            if on_progress:
                # 模拟进度更新
                total_size = len(content)
                for progress in range(0, 101, 10):
                    on_progress('uploading' if progress < 100 else 'success', {
                        'progress': progress,
                        'rest_time': (100 - progress) / 10,
                        'speed': total_size / 10
                    })
                    time.sleep(0.1)
            
            # 上传到 MinIO
            url = await minio_service.upload_file(
                content,
                path_metadata["pathname"],
                file.content_type
            )
            
            metadata = FileMetadata(
                date=path_metadata["date"],
                dirname=path_metadata["dirname"],
                filename=path_metadata["filename"],
                path=path_metadata["pathname"]
            )
            
            return UploadResponse(data=metadata, success=True)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
