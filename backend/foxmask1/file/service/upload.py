import base64
import time
import hashlib
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException, UploadFile
import logging

from ..services.minio import minio_service
from ..models.file import FileMetadata, UploadResponse, UploadBase64ToS3Result
from ..utils.file import generate_file_path_metadata, parse_data_uri
from ..utils.hash import sha256_hash

# 设置日志记录器
logger = logging.getLogger(__name__)

class UploadService:
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
        logger.info(
            "开始上传文件到MinIO - 文件名: %s, 目录: %s, 路径名: %s, 跳过类型检查: %s",
            file.filename, directory, pathname, skip_check_file_type
        )
        
        # 检查文件类型
        if not skip_check_file_type and not file.content_type.startswith('image'):
            logger.warning(
                "文件类型不支持 - 文件名: %s, 内容类型: %s",
                file.filename, file.content_type
            )
            if on_not_supported:
                logger.debug("执行不支持文件类型的回调函数")
                on_not_supported()
            return UploadResponse(success=False, message="File type not supported")
        
        # 生成文件路径
        path_metadata = generate_file_path_metadata(file.filename, directory, pathname)
        logger.debug(
            "生成文件路径元数据 - 文件名: %s, 最终路径: %s",
            file.filename, path_metadata["pathname"]
        )
        
        try:
            # 流式上传到 MinIO
            logger.info("开始流式上传到MinIO - 文件名: %s", file.filename)
            url = await minio_service.upload_file_stream(
                file,
                path_metadata["pathname"]
            )
            
            metadata = FileMetadata(
                date=path_metadata["date"],
                dirname=path_metadata["dirname"],
                filename=path_metadata["filename"],
                path=path_metadata["pathname"]
            )
            
            logger.info(
                "文件上传成功 - 文件名: %s, MinIO路径: %s, URL: %s",
                file.filename, path_metadata["pathname"], url
            )
            
            return UploadResponse(data=metadata, success=True)
            
        except Exception as e:
            logger.error(
                "文件上传到MinIO失败 - 文件名: %s, 错误: %s",
                file.filename, str(e), exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

        
    async def calculate_file_hash(self, file: UploadFile) -> str:
        """计算文件哈希（流式处理，支持大文件）"""
        logger.debug("开始计算文件哈希 - 文件名: %s", file.filename)
        
        hash_sha256 = hashlib.sha256()
        # 重置文件指针到开始
        await file.seek(0)
        
        # 分块读取文件计算哈希
        chunk_size = 8192  # 8KB chunks
        total_chunks = 0
        total_bytes = 0
        
        try:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                hash_sha256.update(chunk)
                total_chunks += 1
                total_bytes += len(chunk)
            
            file_hash = hash_sha256.hexdigest()
            
            logger.debug(
                "文件哈希计算完成 - 文件名: %s, 哈希: %s, 总块数: %s, 总字节: %s",
                file.filename, file_hash, total_chunks, total_bytes
            )
            
            # 重置文件指针
            await file.seek(0)
            return file_hash
            
        except Exception as e:
            logger.error(
                "文件哈希计算失败 - 文件名: %s, 错误: %s",
                file.filename, str(e), exc_info=True
            )
            # 确保文件指针重置
            try:
                await file.seek(0)
            except:
                pass
            raise

    async def upload_base64_to_minio(
        self,
        base64_data: str,
        filename: Optional[str] = None,
        directory: Optional[str] = None,
        pathname: Optional[str] = None
    ) -> UploadBase64ToS3Result:
        """上传 base64 数据到 MinIO"""
        logger.info(
            "开始上传Base64数据到MinIO - 文件名: %s, 目录: %s, 路径名: %s, 数据长度: %s",
            filename, directory, pathname, len(base64_data)
        )
        
        parsed = parse_data_uri(base64_data)
        logger.debug("解析Data URI完成 - MIME类型: %s, 数据类型: %s", parsed["mime_type"], parsed["type"])
        
        if parsed["type"] != "base64" or not parsed["base64"]:
            logger.error("无效的Base64数据 - 数据类型: %s, 是否有Base64内容: %s", parsed["type"], bool(parsed["base64"]))
            raise HTTPException(status_code=400, detail="Invalid base64 data")
        
        try:
            # 解码 base64
            logger.debug("开始解码Base64数据")
            file_data = base64.b64decode(parsed["base64"])
            logger.debug("Base64解码完成 - 解码后数据大小: %s bytes", len(file_data))
            
            # 确定文件名和 MIME 类型
            mime_type = parsed["mime_type"] or "application/octet-stream"
            file_extension = mime_type.split('/')[-1] if '/' in mime_type else "bin"
            
            if not filename:
                filename = f"file_{int(time.time())}.{file_extension}"
                logger.debug("生成自动文件名: %s", filename)
            
            # 计算哈希
            logger.debug("计算文件哈希")
            file_hash = sha256_hash(file_data)
            logger.debug("文件哈希计算完成: %s", file_hash)
            
            # 生成文件路径
            path_metadata = generate_file_path_metadata(filename, directory, pathname)
            logger.debug(
                "生成文件路径 - 文件名: %s, 最终路径: %s",
                filename, path_metadata["pathname"]
            )
            
            # 上传到 MinIO
            logger.info("开始上传到MinIO - 文件名: %s, 大小: %s bytes", filename, len(file_data))
            url = await minio_service.upload_file(
                file_data,
                path_metadata["pathname"],
                mime_type
            )
            
            metadata = FileMetadata(
                date=path_metadata["date"],
                dirname=path_metadata["dirname"],
                filename=path_metadata["filename"],
                path=path_metadata["pathname"]
            )
            
            logger.info(
                "Base64上传成功 - 文件名: %s, MinIO路径: %s, 文件类型: %s, 大小: %s bytes",
                filename, path_metadata["pathname"], mime_type, len(file_data)
            )
            
            return UploadBase64ToS3Result(
                file_type=mime_type,
                hash=file_hash,
                metadata=metadata,
                size=len(file_data),
                url=url
            )
            
        except Exception as e:
            logger.error(
                "Base64上传失败 - 文件名: %s, 错误: %s",
                filename, str(e), exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Base64 upload failed: {str(e)}")

    async def get_signed_upload_url(
        self,
        filename: str,
        directory: Optional[str] = None,
        pathname: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成预签名上传 URL"""
        logger.info(
            "生成预签名URL - 文件名: %s, 目录: %s, 路径名: %s",
            filename, directory, pathname
        )
        
        path_metadata = generate_file_path_metadata(filename, directory, pathname)
        logger.debug(
            "生成预签名URL路径 - 文件名: %s, 最终路径: %s",
            filename, path_metadata["pathname"]
        )
        
        try:
            logger.debug("请求MinIO生成预签名URL")
            presigned_url = await minio_service.get_presigned_put_url(path_metadata["pathname"])
            
            metadata = FileMetadata(
                date=path_metadata["date"],
                dirname=path_metadata["dirname"],
                filename=path_metadata["filename"],
                path=path_metadata["pathname"]
            )
            
            logger.info(
                "预签名URL生成成功 - 文件名: %s, URL: %s, 过期时间: 7天",
                filename, presigned_url
            )
            
            return {
                "pre_sign_url": presigned_url,
                "metadata": metadata,
                "expires": 604800  # 7天
            }
            
        except Exception as e:
            logger.error(
                "预签名URL生成失败 - 文件名: %s, 错误: %s",
                filename, str(e), exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")

upload_service = UploadService()