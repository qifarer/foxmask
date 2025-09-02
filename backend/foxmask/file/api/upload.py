from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import logging

from ..services.upload import upload_service
from ..services.file import file_service
from ..utils.image import get_image_dimensions
from ..utils.hash import sha256_hash
from ..models.file import (
    UploadResponse, 
    UploadBase64ToS3Result, 
    PreSignedUrlResponse,
    UploadWithProgressResult
)
from ..models.upload import (
    UploadBase64Request,
    UploadWithProgressRequest
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
# 可以为特定模块设置不同的日志级别
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/file", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    directory: Optional[str] = Form(None),
    pathname: Optional[str] = Form(None),
    skip_check_file_type: bool = Form(False)
):
    """上传文件到 MinIO"""
    try:
        logger.info(f"开始上传文件: {file.filename}, directory: {directory}, pathname: {pathname}")
        result = await upload_service.upload_file_to_minio(
            file, directory, pathname, skip_check_file_type
        )
        logger.info(f"文件上传成功: {file.filename}, 路径: {result.data.path if result.success else '未知'}")
        return result
    except Exception as e:
        logger.error(f"文件上传失败: {file.filename}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/base64", response_model=UploadBase64ToS3Result)
async def upload_base64(request: UploadBase64Request):
    """上传 base64 数据到 MinIO"""
    try:
        logger.info(f"开始上传base64文件: {request.filename}")
        result = await upload_service.upload_base64_to_minio(
            request.base64_data, request.filename, request.directory, request.pathname
        )
        logger.info(f"base64文件上传成功: {request.filename}")
        return result
    except Exception as e:
        logger.error(f"base64文件上传失败: {request.filename}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"base64文件上传失败: {str(e)}")

@router.post("/with-progress", response_model=UploadWithProgressResult)
async def upload_with_progress(
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Form(None),
    skip_check_file_type: bool = Form(False)
):
    """带进度上传文件（完整流程）"""
    try:
        logger.info(f"开始带进度上传文件: {file.filename}, knowledge_base_id: {knowledge_base_id}")
        
        # 1. 获取图片尺寸
        dimensions = await get_image_dimensions(file)
        logger.debug(f"文件尺寸获取成功: {dimensions}")
        
        # 2. 计算文件哈希（流式处理，避免内存问题）
        file_hash = await upload_service.calculate_file_hash(file)
        logger.debug(f"文件哈希计算完成: {file_hash}")
            
        # 3. 检查文件是否已存在
        check_status = await file_service.check_file_hash(file_hash)
        logger.debug(f"文件存在性检查完成: 已存在={check_status.is_exist}")
        
        if check_status.is_exist:
            logger.info(f"文件已存在，跳过上传: {file.filename}, 哈希: {file_hash}")
            return UploadWithProgressResult(
                id="existing_file",  # 需要从数据库获取实际ID
                url=check_status.url,
                dimensions=dimensions,
                filename=file.filename
            )
        
        # 4. 上传文件到 MinIO
        upload_result = await upload_service.upload_file_to_minio(
            file,
            skip_check_file_type=skip_check_file_type
        )
        
        if not upload_result.success:
            logger.error(f"MinIO上传失败: {file.filename}")
            raise HTTPException(status_code=400, detail="Upload failed")
        
        logger.info(f"MinIO上传成功: {file.filename}, 路径: {upload_result.data.path}")
        
        # 5. 检测文件类型
        file_type = file.content_type or "application/octet-stream"
        logger.debug(f"文件类型检测: {file_type}")
        
        # 6. 获取文件大小
        file.file.seek(0, 2)   # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)      # 重置文件指针
        logger.debug(f"文件大小: {file_size} bytes")

        # 7. 创建文件记录
        from ..models.file import FileCreateRequest
        file_data = FileCreateRequest(
            name=file.filename,
            file_type=file_type,
            hash=file_hash,
            size=file_size,
            url=upload_result.data.path,
            metadata=upload_result.data
        )
        
        created_file = await file_service.create_file(file_data, knowledge_base_id)
        logger.info(f"文件记录创建成功: ID={created_file.id}, 文件名={file.filename}")
        
        return UploadWithProgressResult(
            id=created_file.id,
            url=created_file.url,
            dimensions=dimensions,
            filename=file.filename
        )
    except Exception as e:
        # 确保文件指针重置
        try:
            await file.seek(0)
        except:
            pass
        logger.error(f"带进度上传失败: {file.filename}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/presigned-url", response_model=PreSignedUrlResponse)
async def get_presigned_url(
    filename: str,
    directory: Optional[str] = None,
    pathname: Optional[str] = None
):
    """获取预签名上传 URL"""
    try:
        logger.info(f"请求预签名URL: filename={filename}, directory={directory}, pathname={pathname}")
        result = await upload_service.get_signed_upload_url(
            filename, directory, pathname
        )
        logger.info(f"预签名URL生成成功: {filename}")
        return PreSignedUrlResponse(**result)
    except Exception as e:
        logger.error(f"预签名URL生成失败: {filename}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预签名URL生成失败: {str(e)}")