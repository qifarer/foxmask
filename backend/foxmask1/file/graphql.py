# foxmask/file/graphql.py
import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging
import base64

from foxmask.file.models import File, FileStatus, FileType, StorageProvider, FileChunk
from foxmask.file.services import file_service
from foxmask.auth.schemas import User
from foxmask.core.exceptions import NotFoundError, ServiceError, ValidationError

logger = logging.getLogger(__name__)

@strawberry.type
class FileType:
    id: strawberry.ID
    file_id: strawberry.ID
    filename: str
    original_filename: str
    content_type: str
    extension: str
    file_type: str
    size: int
    status: str
    storage_provider: str
    bucket_name: str
    object_key: str
    owner_id: str
    tenant_id: Optional[str]
    project_id: Optional[str]
    is_public: bool
    metadata: strawberry.scalars.JSON
    tags: List[str]
    version: int
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_deleted: bool
    deleted_at: Optional[datetime]

@strawberry.type
class FileChunkType:
    id: strawberry.ID
    file_id: strawberry.ID
    chunk_number: int
    chunk_size: int
    total_chunks: int
    storage_provider: str
    bucket_name: str
    object_key: str
    checksum: str
    is_uploaded: bool
    created_at: datetime
    uploaded_at: Optional[datetime]

@strawberry.input
class FileUploadInput:
    filename: str
    content_type: str
    size: int
    file_type: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = False
    metadata: Optional[strawberry.scalars.JSON] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None

@strawberry.input
class FileUpdateInput:
    filename: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    metadata: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class FileChunkUploadInput:
    file_id: strawberry.ID
    chunk_number: int
    chunk_size: int
    total_chunks: int
    chunk_data: str  # 使用base64编码的字符串代替bytes

@strawberry.input
class FileSearchInput:
    query: Optional[str] = None
    file_type: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    skip: int = 0
    limit: int = 100

@strawberry.type
class FileConnection:
    items: List[FileType]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool

@strawberry.type
class MutationResult:
    success: bool
    message: Optional[str] = None
    id: Optional[strawberry.ID] = None

def _convert_file_to_type(file: File) -> FileType:
    """将File模型转换为GraphQL类型"""
    return FileType(
        id=str(file.id),
        file_id=str(file.file_id),
        filename=file.filename,
        original_filename=file.original_filename,
        content_type=file.content_type,
        extension=file.extension,
        file_type=file.file_type.value,
        size=file.size,
        status=file.status.value,
        storage_provider=file.storage_provider.value,
        bucket_name=file.bucket_name,
        object_key=file.object_key,
        owner_id=file.owner_id,
        tenant_id=file.tenant_id,
        project_id=file.project_id,
        is_public=file.is_public,
        metadata=file.metadata,
        tags=file.tags,
        version=file.version,
        created_at=file.created_at,
        updated_at=file.updated_at,
        accessed_at=file.accessed_at,
        expires_at=file.expires_at,
        is_deleted=file.is_deleted,
        deleted_at=file.deleted_at
    )

def _convert_file_chunk_to_type(chunk: FileChunk) -> FileChunkType:
    """将FileChunk模型转换为GraphQL类型"""
    return FileChunkType(
        id=str(chunk.id),
        file_id=str(chunk.file_id),
        chunk_number=chunk.chunk_number,
        chunk_size=chunk.chunk_size,
        total_chunks=chunk.total_chunks,
        storage_provider=chunk.storage_provider.value,
        bucket_name=chunk.bucket_name,
        object_key=chunk.object_key,
        checksum=chunk.checksum,
        is_uploaded=chunk.is_uploaded,
        created_at=chunk.created_at,
        uploaded_at=chunk.uploaded_at
    )

@strawberry.type
class FileMutation:
    @strawberry.mutation
    async def upload_file(self, info, input: FileUploadInput) -> MutationResult:
        """上传文件"""
        try:
            # 获取当前用户
            user = info.context["user"]
            
            # 确定存储路径
            bucket_name = "default"
            object_key = input.filename
            
            # 创建文件记录
            file_obj = await file_service.create_file(
                filename=input.filename,
                size=input.size,
                content_type=input.content_type,
                owner_id=user.user_id,
                bucket_name=bucket_name,
                object_key=object_key,
                file_type=FileType(input.file_type) if input.file_type else FileType.OTHER,
                user=user,
                tenant_id=input.tenant_id or user.tenant_id,
                project_id=input.project_id,
                tags=input.tags,
                is_public=input.is_public or False,
                metadata=input.metadata or {}
            )
            
            return MutationResult(
                success=True,
                message="File upload initiated successfully",
                id=str(file_obj.id)
            )
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return MutationResult(
                success=False,
                message=f"Failed to upload file: {str(e)}"
            )

    @strawberry.mutation
    async def upload_file_chunk(self, info, input: FileChunkUploadInput) -> MutationResult:
        """上传文件分块"""
        try:
            user = info.context["user"]
            
            # 解码base64数据
            try:
                chunk_data = base64.b64decode(input.chunk_data)
            except Exception as e:
                return MutationResult(
                    success=False,
                    message=f"Invalid chunk data format: {str(e)}"
                )
            
            success = await file_service.upload_file_chunk(
                input.file_id,
                input.chunk_number,
                chunk_data,
                user
            )
            
            return MutationResult(
                success=success,
                message="File chunk uploaded successfully" if success else "Failed to upload file chunk"
            )
            
        except ValidationError as e:
            return MutationResult(
                success=False,
                message=f"Validation error: {str(e)}"
            )
        except NotFoundError as e:
            return MutationResult(
                success=False,
                message=f"File not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to upload file chunk: {e}")
            return MutationResult(
                success=False,
                message=f"Failed to upload file chunk: {str(e)}"
            )

    @strawberry.mutation
    async def complete_file_upload(self, info, file_id: strawberry.ID) -> MutationResult:
        """完成文件上传"""
        try:
            user = info.context["user"]
            
            file_obj = await file_service.complete_file_upload(file_id, user)
            
            return MutationResult(
                success=True,
                message="File upload completed successfully",
                id=file_id
            )
            
        except ValidationError as e:
            return MutationResult(
                success=False,
                message=f"Validation error: {str(e)}"
            )
        except NotFoundError as e:
            return MutationResult(
                success=False,
                message=f"File not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to complete file upload: {e}")
            return MutationResult(
                success=False,
                message=f"Failed to complete file upload: {str(e)}"
            )

    @strawberry.mutation
    async def update_file(self, info, file_id: strawberry.ID, input: FileUpdateInput) -> MutationResult:
        """更新文件信息"""
        try:
            user = info.context["user"]
            
            updates = {}
            if input.filename is not None:
                updates["filename"] = input.filename
            if input.tags is not None:
                updates["tags"] = input.tags
            if input.is_public is not None:
                updates["is_public"] = input.is_public
            if input.metadata is not None:
                updates["metadata"] = input.metadata
            
            file_obj = await file_service.update_file(file_id, user, updates)
            
            return MutationResult(
                success=True,
                message="File updated successfully",
                id=file_id
            )
            
        except ValidationError as e:
            return MutationResult(
                success=False,
                message=f"Validation error: {str(e)}"
            )
        except NotFoundError as e:
            return MutationResult(
                success=False,
                message=f"File not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to update file: {e}")
            return MutationResult(
                success=False,
                message=f"Failed to update file: {str(e)}"
            )

    @strawberry.mutation
    async def delete_file(self, info, file_id: strawberry.ID) -> MutationResult:
        """删除文件"""
        try:
            user = info.context["user"]
            
            success = await file_service.delete_file(file_id, user)
            
            if not success:
                return MutationResult(
                    success=False,
                    message="File not found"
                )
            
            return MutationResult(
                success=True,
                message="File deleted successfully"
            )
            
        except ValidationError as e:
            return MutationResult(
                success=False,
                message=f"Validation error: {str(e)}"
            )
        except NotFoundError as e:
            return MutationResult(
                success=False,
                message=f"File not found: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return MutationResult(
                success=False,
                message=f"Failed to delete file: {str(e)}"
            )

@strawberry.type
class FileQuery:
    @strawberry.field
    async def files(self, info, skip: int = 0, limit: int = 100) -> FileConnection:
        """获取文件列表"""
        try:
            user = info.context["user"]
            
            files = await file_service.list_files(user, skip, limit)
            total_count = await File.find({"is_deleted": False}).count()
            
            has_next = total_count > skip + limit
            has_prev = skip > 0
            
            return FileConnection(
                items=[_convert_file_to_type(file) for file in files],
                total=total_count,
                page=skip // limit + 1,
                size=limit,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return FileConnection(
                items=[],
                total=0,
                page=0,
                size=0,
                has_next=False,
                has_prev=False
            )

    @strawberry.field
    async def file(self, info, id: strawberry.ID) -> Optional[FileType]:
        """根据ID获取文件"""
        try:
            user = info.context["user"]
            
            if not ObjectId.is_valid(id):
                return None
                
            file_obj = await file_service.get_file(id, user)
            if not file_obj:
                return None
                
            return _convert_file_to_type(file_obj)
            
        except Exception as e:
            logger.error(f"Failed to get file {id}: {e}")
            return None

    @strawberry.field
    async def search_files(self, info, input: FileSearchInput) -> FileConnection:
        """搜索文件"""
        try:
            user = info.context["user"]
            
            # 构建过滤条件
            filters = {}
            if input.file_type:
                filters["file_type"] = input.file_type
            if input.tags:
                filters["tags"] = {"$in": input.tags}
            if input.is_public is not None:
                filters["is_public"] = input.is_public
            if input.tenant_id:
                filters["tenant_id"] = input.tenant_id
            if input.project_id:
                filters["project_id"] = input.project_id
            
            files = await file_service.list_files(user, input.skip, input.limit, filters)
            total_count = await File.find(filters).count()
            
            has_next = total_count > input.skip + input.limit
            has_prev = input.skip > 0
            
            return FileConnection(
                items=[_convert_file_to_type(file) for file in files],
                total=total_count,
                page=input.skip // input.limit + 1,
                size=input.limit,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except Exception as e:
            logger.error(f"Failed to search files: {e}")
            return FileConnection(
                items=[],
                total=0,
                page=0,
                size=0,
                has_next=False,
                has_prev=False
            )

    @strawberry.field
    async def get_presigned_url(self, info, file_id: strawberry.ID, expires: int = 3600) -> Optional[str]:
        """获取文件下载URL"""
        try:
            user = info.context["user"]
            
            url = await file_service.get_presigned_url(file_id, user, expires)
            return url
            
        except ValidationError:
            return None
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get presigned URL for file {file_id}: {e}")
            return None

# 创建schema
from strawberry.fastapi import GraphQLRouter

file_query = FileQuery()
file_mutation = FileMutation()

schema = strawberry.Schema(query=FileQuery, mutation=FileMutation)
graphql_app = GraphQLRouter(schema)