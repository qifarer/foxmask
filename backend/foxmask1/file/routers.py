# foxmask/file/routers.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query, Path, Body, Form
from typing import List, Optional, Dict, Any
from bson import ObjectId
import logging
import asyncio

# from foxmask.core.casdoor_auth import get_current_user, get_current_active_user, get_admin_user
from foxmask.file.services import file_service
from foxmask.file.schemas import (
    FileResponse, FileListResponse, UploadResponse, PreSignedUrlResponse,
    FileCreateRequest, FileUpdateRequest, FileSearchRequest,
    FileChunkUploadRequest, FileChunkUploadResponse,
    ResponseSchema, PaginatedResponse, UploadWithProgressResult
)
from foxmask.core.exceptions import NotFoundError, ServiceError, ValidationError, AuthenticationError
from foxmask.utils.image import get_image_dimensions
from foxmask.utils.hash import sha256_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

async def get_current_active_user() -> Dict[str, Any]:
    return {"id": "foxmask", "name": "foxmask", "email": "foxmask"}  # TODO: 临时占位
async def get_current_user() -> Dict[str, Any]:
    return {"id": "foxmask", "name": "foxmask", "email": "foxmask"}  # TODO: 临时占位
async def get_admin_user() -> Dict[str, Any]:
    return {"id": "foxmask", "name": "foxmask", "email": "foxmask"}  # TODO: 临时占位
 


@router.post("/upload", response_model=ResponseSchema, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    directory: Optional[str] = Form(None),
    pathname: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None),
    is_public: bool = Form(False),
    skip_check_file_type: bool = Form(False),
    current_user: dict = Depends(get_current_active_user)
):
    """
    上传文件到存储系统
    """
    try:
        logger.info(f"开始上传文件: {file.filename}, user: {current_user.get('id')}")
        
        # 读取文件内容
        content = await file.read()
        
        # 计算文件哈希
        file_hash = sha256_hash(content)
        logger.debug(f"文件哈希计算完成: {file_hash}")
        
        # 检查文件是否已存在
        existing_file = await file_service._check_existing_file(file_hash, current_user)
        if existing_file:
            logger.info(f"文件已存在，跳过上传: {file.filename}, 文件ID: {existing_file.id}")
            return ResponseSchema(
                success=True,
                message="File already exists",
                data={
                    "file_id": str(existing_file.id),
                    "filename": file.filename,
                    "url": await file_service.get_presigned_url(str(existing_file.id), current_user),
                    "existing": True
                }
            )
        
        # 获取图片尺寸（如果是图片）
        dimensions = None
        if file.content_type and file.content_type.startswith('image/'):
            dimensions = await get_image_dimensions(content)
            logger.debug(f"图片尺寸获取成功: {dimensions}")
        
        # 确定存储路径
        bucket_name = "default"
        object_key = f"{directory}/{file.filename}" if directory else file.filename
        
        # 确定文件类型（同步调用）
        file_type = file_service._determine_file_type(file.filename)
        logger.debug(f"Determined file type: {file_type} for filename: {file.filename}")
        
        # 创建文件记录
        file_obj = await file_service.create_file(
            filename=file.filename,
            size=len(content),
            content_type=file.content_type or "application/octet-stream",
            owner_id=current_user.get("id"),
            bucket_name=bucket_name,
            object_key=object_key,
            file_type=file_type,  # 传递确定的文件类型
            user=current_user,
            tenant_id=current_user.get("tenant_id", current_user.get("casdoor_org")),
            tags=tags,
            is_public=is_public,
            metadata={
                "dimensions": dimensions,
                "original_filename": file.filename,
                "hash": file_hash
            }
        )
        
        # 上传文件到存储
        await file_service._upload_to_storage(bucket_name, object_key, content)
        
        # 标记为已处理
        await file_service.complete_file_upload(str(file_obj.id), current_user)
        
        logger.info(f"文件上传成功: {file.filename}, 文件ID: {file_obj.id}")
        
        return ResponseSchema(
            success=True,
            message="File uploaded successfully",
            data={
                "file_id": str(file_obj.id),
                "filename": file.filename,
                "url": await file_service.get_presigned_url(str(file_obj.id), current_user),
                "dimensions": dimensions,
                "existing": False
            }
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {file.filename}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )

@router.post("/upload-with-progress", response_model=UploadWithProgressResult)
async def upload_with_progress(
    file: UploadFile = File(...),
    knowledge_base_id: Optional[str] = Form(None),
    tags: Optional[List[str]] = Form(None),
    is_public: bool = Form(False),
    skip_check_file_type: bool = Form(False),
    current_user: dict = Depends(get_current_active_user)  # 需要活跃用户
):
    """
    带进度上传文件（完整流程）
    """
    try:
        logger.info(f"开始带进度上传文件: {file.filename}, user: {current_user.get('id')}")
        
        # 1. 获取图片尺寸
        content = await file.read()
        dimensions = None
        if file.content_type and file.content_type.startswith('image/'):
            dimensions = await get_image_dimensions(content)
            logger.debug(f"文件尺寸获取成功: {dimensions}")
        
        # 2. 计算文件哈希
        file_hash = sha256_hash(content)
        logger.debug(f"文件哈希计算完成: {file_hash}")
            
        # 3. 检查文件是否已存在
        existing_file = await file_service._check_existing_file(file_hash, current_user)
        if existing_file:
            logger.info(f"文件已存在，跳过上传: {file.filename}")
            return UploadWithProgressResult(
                id=str(existing_file.id),
                url=await file_service.get_presigned_url(str(existing_file.id), current_user),
                dimensions=dimensions,
                filename=file.filename
            )
        
        # 4. 确定存储路径
        bucket_name = "default"
        object_key = file.filename
        
        # 5. 创建文件记录
        file_obj = await file_service.create_file(
            filename=file.filename,
            size=len(content),
            content_type=file.content_type or "application/octet-stream",
            owner_id=current_user.get("id"),
            bucket_name=bucket_name,
            object_key=object_key,
            file_type=file_service._determine_file_type(file.filename),
            user=current_user,
            tenant_id=current_user.get("tenant_id", current_user.get("casdoor_org")),
            tags=tags,
            is_public=is_public,
            metadata={
                "dimensions": dimensions,
                "original_filename": file.filename,
                "hash": file_hash,
                "knowledge_base_id": knowledge_base_id
            }
        )
        
        # 6. 上传文件到存储
        await file_service._upload_to_storage(bucket_name, object_key, content)
        
        # 7. 标记为已处理
        await file_service.complete_file_upload(str(file_obj.id), current_user)
        
        logger.info(f"带进度上传成功: {file.filename}, 文件ID: {file_obj.id}")
        
        return UploadWithProgressResult(
            id=str(file_obj.id),
            url=await file_service.get_presigned_url(str(file_obj.id), current_user),
            dimensions=dimensions,
            filename=file.filename
        )
        
    except Exception as e:
        logger.error(f"带进度上传失败: {file.filename}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"带进度上传失败: {str(e)}"
        )

@router.post("/upload-chunk", response_model=FileChunkUploadResponse)
async def upload_chunk(
    request: FileChunkUploadRequest = Body(...),
    chunk_data: bytes = Body(...),
    current_user: dict = Depends(get_current_active_user)  # 需要活跃用户
):
    """
    上传文件分块
    """
    try:
        success = await file_service.upload_file_chunk(
            request.file_id,
            request.chunk_number,
            chunk_data,
            current_user
        )
        
        return FileChunkUploadResponse(
            success=success,
            chunk_number=request.chunk_number,
            uploaded_size=len(chunk_data),
            total_size=request.chunk_size
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/complete-upload/{file_id}", response_model=ResponseSchema)
async def complete_upload(
    file_id: str = Path(..., description="文件ID"),
    current_user: dict = Depends(get_current_active_user)  # 需要活跃用户
):
    """
    完成文件上传
    """
    try:
        file_obj = await file_service.complete_file_upload(file_id, current_user)
        
        return ResponseSchema(
            success=True,
            message="File upload completed successfully",
            data={
                "file_id": file_id,
                "status": file_obj.status.value,
                "url": await file_service.get_presigned_url(file_id, current_user)
            }
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/presigned-url", response_model=PreSignedUrlResponse)
async def get_presigned_url(
    filename: str = Query(..., description="文件名称"),
    content_type: str = Query("application/octet-stream", description="内容类型"),
    expires: int = Query(3600, ge=60, le=604800, description="过期时间（秒）"),
    current_user: dict = Depends(get_current_user)  # 普通用户即可
):
    """
    获取预签名URL（用于客户端直接上传）
    """
    try:
        # 这里需要实现生成预签名URL的逻辑
        # 暂时返回模拟数据
        return PreSignedUrlResponse(
            pre_sign_url=f"https://minio.example.com/upload/{filename}",
            metadata={
                "filename": filename,
                "content_type": content_type
            },
            expires_in=expires
        )
        
    except Exception as e:
        logger.error(f"预签名URL生成失败: {filename}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预签名URL生成失败: {str(e)}"
        )

@router.get("", response_model=PaginatedResponse)
async def list_files(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    file_type: Optional[str] = Query(None, description="文件类型"),
    tags: Optional[List[str]] = Query(None, description="标签列表"),
    current_user: dict = Depends(get_current_user)  # 普通用户即可
):
    """
    获取文件列表
    """
    try:
        filters = {}
        if file_type:
            filters["file_type"] = file_type
        if tags:
            filters["tags"] = {"$in": tags}
        
        files = await file_service.list_files(current_user, skip, limit, filters)
        total_count = len(files)  # 简化处理
        
        return PaginatedResponse(
            total=total_count,
            page=skip // limit + 1,
            size=limit,
            items=files
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str = Path(..., description="文件ID"),
    current_user: dict = Depends(get_current_user)  # 普通用户即可
):
    """
    获取文件信息
    """
    try:
        file_obj = await file_service.get_file(file_id, current_user)
        if not file_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        return file_obj
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.get("/{file_id}/download-url", response_model=PreSignedUrlResponse)
async def get_download_url(
    file_id: str = Path(..., description="文件ID"),
    expires: int = Query(3600, ge=60, le=604800, description="过期时间（秒）"),
    current_user: dict = Depends(get_current_user)  # 普通用户即可
):
    """
    获取文件下载URL
    """
    try:
        url = await file_service.get_presigned_url(file_id, current_user, expires)
        
        file_obj = await file_service.get_file(file_id, current_user)
        if not file_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return PreSignedUrlResponse(
            pre_sign_url=url,
            metadata={
                "filename": file_obj.filename,
                "size": file_obj.size,
                "content_type": file_obj.content_type
            },
            expires_in=expires
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.delete("/{file_id}", response_model=ResponseSchema)
async def delete_file(
    file_id: str = Path(..., description="文件ID"),
    current_user: dict = Depends(get_admin_user)  # 需要管理员权限
):
    """
    删除文件（需要管理员权限）
    """
    try:
        success = await file_service.delete_file(file_id, current_user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return ResponseSchema(
            success=True,
            message="File deleted successfully"
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

# 新增：文件更新端点（需要文件所有者或管理员权限）
@router.put("/{file_id}", response_model=ResponseSchema)
async def update_file(
    file_id: str = Path(..., description="文件ID"),
    update_data: FileUpdateRequest = Body(...),
    current_user: dict = Depends(get_current_active_user)  # 需要活跃用户
):
    """
    更新文件信息（需要文件所有者或管理员权限）
    """
    try:
        # 检查用户权限
        file_obj = await file_service.get_file(file_id, current_user)
        if not file_obj:
            raise NotFoundError("File not found")
        
        # 检查是否是文件所有者或管理员
        if (file_obj.owner_id != current_user.get("id") and 
            "admin" not in current_user.get("roles", []) and
            "administrator" not in current_user.get("roles", [])):
            raise AuthenticationError("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        
        updated_file = await file_service.update_file(file_id, update_data.dict(exclude_unset=True), current_user)
        
        return ResponseSchema(
            success=True,
            message="File updated successfully",
            data={"file_id": file_id}
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )