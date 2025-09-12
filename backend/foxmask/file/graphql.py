# -*- coding: utf-8 -*-
# foxmask/file/graphql.py
# GraphQL schema and resolvers for file metadata management

import strawberry
from enum import Enum
from typing import Optional, List, Dict, Any
from strawberry.types import Info
from strawberry.scalars import JSON
from .models import File, FileStatus, FileVisibility, FileType as FileTypeModel, FileChunk
from .services import file_service
from foxmask.shared.dependencies import get_user_from_token
from foxmask.utils.helpers import get_current_time
from fastapi import Depends, HTTPException, status
from functools import wraps

# API Key context dependency for GraphQL
async def get_api_key_context(info: Info) -> Dict[str, Any]:
    """Get API key context from GraphQL info"""
    request = info.context["request"]
    # Use the existing API key validation
    api_key_info = await get_user_from_token(request)
    return api_key_info

def api_key_required(permission: str = "read"):
    """Decorator to require API key authentication for GraphQL resolvers"""
    def decorator(resolver):
        @wraps(resolver)
        async def wrapper(*args, **kwargs):
            info = kwargs.get('info') or args[-1] if args else None
            if not info or not hasattr(info, 'context'):
                raise Exception("Authentication required")
            
            request = info.context.get("request")
            if not request:
                raise Exception("Request context not available")
            
            # Use appropriate permission dependency
            if permission == "read":
                api_key_info = await get_user_from_token(request)
            elif permission == "write":
                api_key_info = await get_user_from_token(request)
            else:
                api_key_info = await get_user_from_token(request)
            
            # Store API key info in context for later use
            info.context["api_key_info"] = api_key_info
            return await resolver(*args, **kwargs)
        return wrapper
    return decorator

# 修复：使用正确的 Enum 继承
@strawberry.enum
class FileStatusEnum(Enum):
    """GraphQL file status enum"""
    DRAFT = "draft"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELED = "canceled"

@strawberry.enum
class FileVisibilityEnum(Enum):
    """GraphQL file visibility enum"""
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"

@strawberry.enum
class FileTypeEnum(Enum):
    """GraphQL file type enum"""
    PDF = "pdf"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    VECTOR = "vector"
    AUDIO = "audio"
    VIDEO = "video"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    ARCHIVE = "archive"
    BINARY = "binary"
    UNKNOWN = "unknown"

@strawberry.type
class FileType:
    """GraphQL file type"""
    id: strawberry.ID
    filename: str
    file_size: int
    content_type: str
    file_type: FileTypeEnum
    extension: str
    minio_object_name: str
    minio_bucket: str
    minio_etag: Optional[str]
    minio_url: Optional[str]
    status: FileStatusEnum
    upload_progress: float
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    checksum_crc32: Optional[str]
    uploaded_by: str
    tenant_id: str
    visibility: FileVisibilityEnum
    allowed_users: List[str]
    allowed_roles: List[str]
    tags: List[str]
    categories: List[str]
    description: Optional[str]
    metadata: JSON  # 修改这里：使用 JSON scalar 而不是 Dict[str, Any]
    is_multipart: bool
    upload_id: Optional[str]
    chunk_size: int
    total_chunks: int
    uploaded_chunks: int
    verified_chunks: int
    created_at: str
    updated_at: str
    uploaded_at: Optional[str]
    processed_at: Optional[str]
    expires_at: Optional[str]
    version: int
    previous_version: Optional[str]
    is_latest: bool
    download_count: int
    view_count: int
    last_downloaded_at: Optional[str]
    last_viewed_at: Optional[str]

@strawberry.input
class FileCreateInput:
    """GraphQL file creation input"""
    filename: str
    file_size: int
    content_type: str
    description: Optional[str] = None
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    categories: Optional[List[str]] = strawberry.field(default_factory=list)
    visibility: Optional[FileVisibilityEnum] = FileVisibilityEnum.PRIVATE
    allowed_users: Optional[List[str]] = strawberry.field(default_factory=list)
    allowed_roles: Optional[List[str]] = strawberry.field(default_factory=list)
    metadata: Optional[JSON] = strawberry.field(default_factory=dict)  # 修改这里：使用 JSON 而不是 Dict[str, Any]
    chunk_size: Optional[int] = 5 * 1024 * 1024  # 5MB default

@strawberry.input
class FileUpdateInput:
    """GraphQL file update input"""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    visibility: Optional[FileVisibilityEnum] = None
    allowed_users: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    metadata: Optional[JSON] = None  # 修改这里：使用 JSON 而不是 Dict[str, Any]


@strawberry.type
class UploadProgress:
    """GraphQL upload progress type"""
    file_id: str
    filename: str
    status: FileStatusEnum
    uploaded_chunks: int
    total_chunks: int
    progress_percentage: float

@strawberry.type
class FileChunkType:
    """GraphQL file chunk type"""
    id: strawberry.ID
    file_id: str
    upload_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    minio_object_name: str
    minio_bucket: str
    minio_etag: Optional[str]
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    status: str
    retry_count: int
    created_at: str
    uploaded_at: Optional[str]
    verified_at: Optional[str]
    error_message: Optional[str]

@strawberry.type
class APIKeyInfo:
    """GraphQL API key information type"""
    api_key_id: str
    user_id: str
    permissions: List[str]
    client_ip: Optional[str]

def file_to_gql(file: File) -> FileType:
    """Convert File model to GraphQL type"""
    return FileType(
        id=strawberry.ID(str(file.id)),
        filename=file.filename,
        file_size=file.file_size,
        content_type=file.content_type,
        file_type=FileTypeEnum[file.file_type.name] if file.file_type else FileTypeEnum.UNKNOWN,
        extension=file.extension,
        minio_object_name=file.minio_object_name,
        minio_bucket=file.minio_bucket,
        minio_etag=file.minio_etag,
        minio_url=str(file.minio_url) if file.minio_url else None,
        status=FileStatusEnum[file.status.name] if file.status else FileStatusEnum.DRAFT,
        upload_progress=file.upload_progress,
        checksum_md5=file.checksum_md5,
        checksum_sha256=file.checksum_sha256,
        checksum_crc32=file.checksum_crc32,
        uploaded_by=file.uploaded_by,
        tenant_id=file.tenant_id,
        visibility=FileVisibilityEnum[file.visibility.name] if file.visibility else FileVisibilityEnum.PRIVATE,
        allowed_users=file.allowed_users,
        allowed_roles=file.allowed_roles,
        tags=file.tags,
        categories=file.categories,
        description=file.description,
        metadata=file.metadata,  # 这里保持原样，JSON scalar 会自动处理
        is_multipart=file.is_multipart,
        upload_id=file.upload_id,
        chunk_size=file.chunk_size,
        total_chunks=file.total_chunks,
        uploaded_chunks=file.uploaded_chunks,
        verified_chunks=file.verified_chunks,
        created_at=file.created_at.isoformat() if file.created_at else get_current_time().isoformat(),
        updated_at=file.updated_at.isoformat() if file.updated_at else get_current_time().isoformat(),
        uploaded_at=file.uploaded_at.isoformat() if file.uploaded_at else None,
        processed_at=file.processed_at.isoformat() if file.processed_at else None,
        expires_at=file.expires_at.isoformat() if file.expires_at else None,
        version=file.version,
        previous_version=file.previous_version,
        is_latest=file.is_latest,
        download_count=file.download_count,
        view_count=file.view_count,
        last_downloaded_at=file.last_downloaded_at.isoformat() if file.last_downloaded_at else None,
        last_viewed_at=file.last_viewed_at.isoformat() if file.last_viewed_at else None
    )

def chunk_to_gql(chunk: FileChunk) -> FileChunkType:
    """Convert FileChunk model to GraphQL type"""
    return FileChunkType(
        id=strawberry.ID(str(chunk.id)),
        file_id=chunk.file_id,
        upload_id=chunk.upload_id,
        chunk_number=chunk.chunk_number,
        chunk_size=chunk.chunk_size,
        start_byte=chunk.start_byte,
        end_byte=chunk.end_byte,
        minio_object_name=chunk.minio_object_name,
        minio_bucket=chunk.minio_bucket,
        minio_etag=chunk.minio_etag,
        checksum_md5=chunk.checksum_md5,
        checksum_sha256=chunk.checksum_sha256,
        status=chunk.status.value if chunk.status else "pending",
        retry_count=chunk.retry_count,
        created_at=chunk.created_at.isoformat() if chunk.created_at else get_current_time().isoformat(),
        uploaded_at=chunk.uploaded_at.isoformat() if chunk.uploaded_at else None,
        verified_at=chunk.verified_at.isoformat() if chunk.verified_at else None,
        error_message=chunk.error_message
    )

@strawberry.type
class FileQuery:
    """GraphQL queries for files"""
    
    @strawberry.field
    @api_key_required("read")
    async def file(self, info: Info, file_id: strawberry.ID) -> FileType:
        """Get file by ID"""
        api_key_info = info.context["api_key_info"]
        file_metadata = await file_service.get_file_metadata(str(file_id))
        
        if not file_metadata:
            raise Exception("File not found")
        
        # Check permission using API key context
        if not await file_service.check_file_access(
            str(file_id), 
            api_key_info["casdoor_user_id"], 
            api_key_info.get("permissions", [])
        ):
            raise Exception("Not authorized to access this file")
        
        return file_to_gql(file_metadata)
    
    @strawberry.field
    @api_key_required("read")
    async def files(
        self, 
        info: Info, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[FileType]:
        """Get user's files"""
        api_key_info = info.context["api_key_info"]
        files = await file_service.list_user_files(api_key_info["casdoor_user_id"], skip, limit)
        
        return [file_to_gql(file) for file in files]
    
    @strawberry.field
    @api_key_required("read")
    async def file_chunks(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> List[FileChunkType]:
        """Get file chunks"""
        api_key_info = info.context["api_key_info"]
        
        # Check permission first
        if not await file_service.check_file_access(
            str(file_id), 
            api_key_info["casdoor_user_id"], 
            api_key_info.get("permissions", [])
        ):
            raise Exception("Not authorized to access this file")
        
        chunks = await FileChunk.find(
            FileChunk.file_id == str(file_id)
        ).to_list()
        
        return [chunk_to_gql(chunk) for chunk in chunks]
    
    @strawberry.field
    @api_key_required("read")
    async def upload_progress(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> UploadProgress:
        """Get upload progress for a file"""
        api_key_info = info.context["api_key_info"]
        
        # Check permission
        if not await file_service.check_file_access(
            str(file_id), 
            api_key_info["casdoor_user_id"], 
            api_key_info.get("permissions", [])
        ):
            raise Exception("Not authorized to access this file")
        
        progress = await file_service.get_upload_progress(str(file_id))
        
        return UploadProgress(
            file_id=progress["file_id"],
            filename=progress["filename"],
            status=FileStatusEnum[progress["status"].name] if progress["status"] else FileStatusEnum.DRAFT,
            uploaded_chunks=progress["uploaded_chunks"],
            total_chunks=progress["total_chunks"],
            progress_percentage=progress["progress_percentage"]
        )
    
    @strawberry.field
    @api_key_required("read")
    async def api_key_info(self, info: Info) -> APIKeyInfo:
        """Get current API key information"""
        api_key_info = info.context["api_key_info"]
        return APIKeyInfo(
            api_key_id=api_key_info["api_key_id"],
            user_id=api_key_info["casdoor_user_id"],
            permissions=api_key_info.get("permissions", []),
            client_ip=api_key_info.get("client_ip")
        )
@strawberry.type
class MultipartUploadResult:
    """GraphQL multipart upload result type"""
    file_id: str
    upload_id: str
    chunk_size: int
    total_chunks: int
    minio_bucket: str
    minio_object_name: str

@strawberry.type
class FileMutation:
    """GraphQL mutations for files"""
    
    @strawberry.mutation
    @api_key_required("write")
    async def create_file(
        self, 
        info: Info, 
        file_data: FileCreateInput,
        tenant_id: str
    ) -> FileType:
        """Create a new file record"""
        api_key_info = info.context["api_key_info"]
        
        # Convert input to dict
        file_dict = {
            "filename": file_data.filename,
            "file_size": file_data.file_size,
            "content_type": file_data.content_type,
            "description": file_data.description,
            "tags": file_data.tags or [],
            "categories": file_data.categories or [],
            "visibility": file_data.visibility.value if file_data.visibility else FileVisibilityModel.PRIVATE,
            "allowed_users": file_data.allowed_users or [],
            "allowed_roles": file_data.allowed_roles or [],
            "metadata": file_data.metadata or {},
            "chunk_size": file_data.chunk_size
        }
        
        file_metadata = await file_service.create_file_metadata(
            file_dict, api_key_info["casdoor_user_id"], tenant_id
        )
        return file_to_gql(file_metadata)
    
    @strawberry.mutation
    @api_key_required("write")
    async def update_file(
        self, 
        info: Info, 
        file_id: strawberry.ID,
        update_data: FileUpdateInput
    ) -> FileType:
        """Update file metadata"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to dict
        update_dict = {}
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.tags is not None:
            update_dict["tags"] = update_data.tags
        if update_data.categories is not None:
            update_dict["categories"] = update_data.categories
        if update_data.visibility is not None:
            update_dict["visibility"] = FileVisibilityModel[update_data.visibility.name]
        if update_data.allowed_users is not None:
            update_dict["allowed_users"] = update_data.allowed_users
        if update_data.allowed_roles is not None:
            update_dict["allowed_roles"] = update_data.allowed_roles
        if update_data.metadata is not None:
            update_dict["metadata"] = update_data.metadata
        
        file_metadata = await file_service.update_file_metadata(
            str(file_id), update_dict, api_key_info["casdoor_user_id"]
        )
        
        if not file_metadata:
            raise Exception("File not found or update failed")
        
        return file_to_gql(file_metadata)
    
    @strawberry.mutation
    @api_key_required("write")
    async def delete_file(
        self, 
        info: Info, 
        file_id: strawberry.ID
    ) -> bool:
        """Delete file"""
        api_key_info = info.context["api_key_info"]
        success = await file_service.delete_file(str(file_id), api_key_info["casdoor_user_id"])
        
        if not success:
            raise Exception("File not found or delete failed")
        
        return True
    
    @strawberry.input
    class ChunkEtagInput:
        """GraphQL chunk etag input"""
        chunk_number: int
        etag: str

    @strawberry.mutation
    @api_key_required("write")
    async def init_multipart_upload(
        self,
        info: Info,
        file_data: FileCreateInput,
        tenant_id: str
    ) -> MultipartUploadResult:  # 修改返回类型
        """Initialize multipart upload"""
        api_key_info = info.context["api_key_info"]
        
        file_dict = {
            "filename": file_data.filename,
            "file_size": file_data.file_size,
            "content_type": file_data.content_type,
            "description": file_data.description,
            "tags": file_data.tags or [],
            "chunk_size": file_data.chunk_size
        }
        
        result = await file_service.init_multipart_upload(file_dict, api_key_info["casdoor_user_id"], tenant_id)
        
        # 返回具体的类型而不是 Dict[str, Any]
        return MultipartUploadResult(
            file_id=result["file_id"],
            upload_id=result["upload_id"],
            chunk_size=result["chunk_size"],
            total_chunks=result["total_chunks"],
            minio_bucket=result["minio_bucket"],
            minio_object_name=result["minio_object_name"]
        )
    
    
    @strawberry.mutation
    @api_key_required("write")
    async def complete_multipart_upload(
        self,
        info: Info,
        file_id: strawberry.ID,
        upload_id: str,
        chunk_etags: JSON
    ) -> FileType:
        """Complete multipart upload"""
        api_key_info = info.context["api_key_info"]
        
        # Convert string keys to integers
        etags_dict = {int(k): v for k, v in chunk_etags.items()}
        
        file_metadata = await file_service.complete_multipart_upload(str(file_id), upload_id, etags_dict)
        return file_to_gql(file_metadata)
    
    @strawberry.mutation
    @api_key_required("write")
    async def abort_multipart_upload(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> bool:
        """Abort multipart upload"""
        api_key_info = info.context["api_key_info"]
        success = await file_service.abort_multipart_upload(str(file_id))
        
        if not success:
            raise Exception("Failed to abort multipart upload")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def increment_download_count(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> bool:
        """Increment file download count"""
        api_key_info = info.context["api_key_info"]
        
        # Check permission first
        if not await file_service.check_file_access(
            str(file_id), 
            api_key_info["casdoor_user_id"], 
            api_key_info.get("permissions", [])
        ):
            raise Exception("Not authorized to access this file")
        
        await file_service.increment_download_count(str(file_id))
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def increment_view_count(
        self,
        info: Info,
        file_id: strawberry.ID
    ) -> bool:
        """Increment file view count"""
        api_key_info = info.context["api_key_info"]
        
        # Check permission first
        if not await file_service.check_file_access(
            str(file_id), 
            api_key_info["casdoor_user_id"], 
            api_key_info.get("permissions", [])
        ):
            raise Exception("Not authorized to access this file")
        
        await file_service.increment_view_count(str(file_id))
        return True

# Schema definition
file_schema = strawberry.Schema(
    query=FileQuery,
    mutation=FileMutation,
    types=[FileType, FileChunkType, UploadProgress, APIKeyInfo]
)