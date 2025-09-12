from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from pydantic import Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from foxmask.utils.helpers import get_current_time  # Assumed to return UTC datetime


class FileStatus(str, Enum):
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

class ChunkStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    FAILED = "failed"

class FileVisibility(str, Enum):
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"

class FileType(str, Enum):
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

class FileChunk(Document):
    file_id: str = Field(..., description="Parent file ID")
    upload_id: str = Field(..., description="MinIO upload ID")
    chunk_number: int = Field(..., ge=1, description="Chunk number (1-based)")
    chunk_size: int = Field(..., ge=0, description="Chunk size in bytes")
    start_byte: int = Field(..., ge=0, description="Start byte position in file")
    end_byte: int = Field(..., ge=0, description="End byte position in file")
    minio_object_name: str = Field(..., description="MinIO object name for this chunk")
    minio_bucket: str = Field(..., description="MinIO bucket name")
    minio_etag: Optional[str] = Field(None, description="MinIO ETag for the chunk")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum")
    status: ChunkStatus = Field(ChunkStatus.PENDING, description="Chunk status")
    retry_count: int = Field(0, description="Number of upload retries")
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = ConfigDict(extra="forbid")

    class Settings:
        name = "file_chunks"
        indexes = [
            IndexModel([("file_id", ASCENDING), ("chunk_number", ASCENDING)], name="file_id_chunk_number", unique=True),
            IndexModel([("file_id", ASCENDING), ("status", ASCENDING)], name="file_id_status"),
            IndexModel([("upload_id", ASCENDING)], name="upload_id"),
            IndexModel([("created_at", ASCENDING)], name="created_at"),
        ]

    def mark_uploaded(self, etag: str, uploaded_at: datetime):
        self.status = ChunkStatus.UPLOADED
        self.minio_etag = etag
        self.uploaded_at = uploaded_at
        self.retry_count = 0

    def mark_verified(self, verified_at: datetime):
        self.status = ChunkStatus.VERIFIED
        self.verified_at = verified_at

    def mark_failed(self, error_message: str):
        self.status = ChunkStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1

class File(Document):
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    file_type: FileType = Field(FileType.UNKNOWN, description="File type category")
    extension: str = Field(..., description="File extension")
    minio_object_name: str = Field(..., description="MinIO object name")
    minio_bucket: str = Field("foxmask", description="MinIO bucket name")
    minio_etag: Optional[str] = Field(None, description="MinIO ETag for complete file")
    minio_version_id: Optional[str] = Field(None, description="MinIO version ID")
    minio_url: Optional[str] = Field(None, description="MinIO access URL")
    status: FileStatus = Field(FileStatus.DRAFT, description="File status")
    upload_progress: float = Field(0.0, ge=0.0, le=100.0, description="Upload progress percentage")
    checksum_md5: Optional[str] = Field(None, description="MD5 checksum of complete file")
    checksum_sha256: Optional[str] = Field(None, description="SHA256 checksum of complete file")
    checksum_crc32: Optional[str] = Field(None, description="CRC32 checksum")
    uploaded_by: str = Field(..., description="User ID who uploaded the file")
    tenant_id: str = Field(..., description="Tenant/organization ID")
    visibility: FileVisibility = Field(FileVisibility.PRIVATE, description="File visibility level")
    allowed_users: List[str] = Field(default_factory=list, description="List of user IDs with access")
    allowed_roles: List[str] = Field(default_factory=list, description="List of roles with access")
    tags: List[str] = Field(default_factory=list, description="File tags for categorization")
    categories: List[str] = Field(default_factory=list, description="File categories")
    description: Optional[str] = Field(None, max_length=1000, description="File description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    is_multipart: bool = Field(False, description="Whether this is a multipart upload")
    upload_id: Optional[str] = Field(None, description="MinIO upload ID for multipart upload")
    chunk_size: int = Field(5 * 1024 * 1024, description="Chunk size in bytes (default 5MB)")
    total_chunks: int = Field(0, ge=0, description="Total number of chunks")
    uploaded_chunks: int = Field(0, ge=0, description="Number of uploaded chunks")
    verified_chunks: int = Field(0, ge=0, description="Number of verified chunks")
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=get_current_time, description="Last update timestamp")
    uploaded_at: Optional[datetime] = Field(None, description="Upload completion timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    version: int = Field(1, ge=1, description="File version")
    previous_version: Optional[str] = Field(None, description="Previous version ID")
    is_latest: bool = Field(True, description="Whether this is the latest version")
    download_count: int = Field(0, ge=0, description="Number of downloads")
    view_count: int = Field(0, ge=0, description="Number of views")
    last_downloaded_at: Optional[datetime] = Field(None, description="Last download timestamp")
    last_viewed_at: Optional[datetime] = Field(None, description="Last view timestamp")

    model_config = ConfigDict(extra="forbid")

    class Settings:
        name = "files"
        indexes = [
            IndexModel([("uploaded_by", ASCENDING)], name="uploaded_by"),
            IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
            IndexModel([("visibility", ASCENDING)], name="visibility"),
            IndexModel([("file_type", ASCENDING)], name="file_type"),
            IndexModel([("tags", ASCENDING)], name="tags"),
            IndexModel([("categories", ASCENDING)], name="categories"),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("created_at", ASCENDING)], name="created_at"),
            IndexModel([("updated_at", ASCENDING)], name="updated_at"),
            IndexModel([("expires_at", ASCENDING)], name="expires_at"),
            IndexModel([("tenant_id", ASCENDING), ("visibility", ASCENDING)], name="tenant_id_visibility"),
            IndexModel([("uploaded_by", ASCENDING), ("status", ASCENDING)], name="uploaded_by_status"),
            IndexModel([("tags", ASCENDING), ("file_type", ASCENDING)], name="tags_file_type"),
        ]

    @field_validator('file_type', mode='before')
    @classmethod
    def determine_file_type(cls, v, values):
        if v != FileType.UNKNOWN:
            return v

        extension = values.get('extension', '').lower()
        content_type = values.get('content_type', '').lower()

        # Prioritize extension-based lookup
        if extension in EXTENSION_FILE_TYPES:
            return EXTENSION_FILE_TYPES[extension]

        # Fallback to content_type
        if any(x in content_type for x in ['pdf', 'document', 'msword', 'wordprocessing']):
            return FileType.PDF if 'pdf' in content_type else FileType.DOCUMENT
        elif any(x in content_type for x in ['spreadsheet', 'excel']):
            return FileType.SPREADSHEET
        elif any(x in content_type for x in ['presentation', 'powerpoint']):
            return FileType.PRESENTATION
        elif any(x in content_type for x in ['text/', 'markdown']):
            return FileType.TEXT
        elif content_type.startswith('image/'):
            return FileType.IMAGE if 'svg' not in content_type else FileType.VECTOR
        elif content_type.startswith('audio/'):
            return FileType.AUDIO
        elif content_type.startswith('video/'):
            return FileType.VIDEO
        elif 'json' in content_type:
            return FileType.JSON
        elif 'xml' in content_type:
            return FileType.XML
        elif 'csv' in content_type:
            return FileType.CSV
        elif any(x in content_type for x in ['zip', 'rar', 'tar', 'gzip', 'compress']):
            return FileType.ARCHIVE
        return FileType.UNKNOWN

    @classmethod
    def to_response_dict(self) -> Dict[str, Any]:
        """转换为响应字典"""
        data = self.dict()
        # 转换 ObjectId 字段
        data['id'] = str(self.id)
        data['uploaded_by'] = str(self.uploaded_by)
        data['tenant_id'] = str(self.tenant_id)
        return data
    
    @field_validator('extension', mode='before')
    @classmethod
    def extract_extension(cls, v, values):
        if v:
            return v.lower()

        filename = values.get('filename', '')
        if '.' not in filename:
            return ''

        # Handle complex extensions like .tar.gz
        parts = filename.rsplit('.', 2)
        if len(parts) > 2 and parts[-2] == 'tar':
            return 'tar.gz'
        return parts[-1].lower()

    def update_status(self, status: FileStatus):
        self.status = status
        self.updated_at = get_current_time()

    def update_progress(self, uploaded: int, verified: int):
        if uploaded > self.total_chunks or verified > self.total_chunks:
            raise ValueError("Uploaded or verified chunks cannot exceed total chunks")
        self.uploaded_chunks = uploaded
        self.verified_chunks = verified
        if self.total_chunks > 0:
            self.upload_progress = (uploaded / self.total_chunks) * 100
        if uploaded == self.total_chunks and verified == self.total_chunks:
            self.status = FileStatus.UPLOADED
            self.uploaded_at = get_current_time()
        elif uploaded > 0:
            self.status = FileStatus.UPLOADING

    def is_upload_complete(self) -> bool:
        return (self.status in [FileStatus.UPLOADED, FileStatus.VERIFIED, FileStatus.COMPLETED] and
                self.uploaded_chunks == self.total_chunks and
                self.verified_chunks == self.total_chunks)

    def can_be_accessed_by(self, user_id: str, user_roles: List[str]) -> bool:
        if self.visibility == FileVisibility.PUBLIC:
            return True
        if user_id == self.uploaded_by:
            return True
        if self.visibility == FileVisibility.TENANT:
            # Implement tenant verification logic here
            return True
        if user_id in self.allowed_users:
            return True
        if any(role in user_roles for role in self.allowed_roles):
            return True
        return False

    def generate_minio_object_name(self) -> str:
        if self.minio_object_name:
            return self.minio_object_name
        timestamp = int(get_current_time().timestamp())
        random_code = uuid.uuid4().hex[:8]
        return f"{self.tenant_id}/{self.uploaded_by}/{timestamp}_{random_code}.{self.extension}"

    def increment_download_count(self):
        self.download_count += 1
        self.last_downloaded_at = get_current_time()
        self.updated_at = get_current_time()

    def increment_view_count(self):
        self.view_count += 1
        self.last_viewed_at = get_current_time()
        self.updated_at = get_current_time()

class FileProcessingJob(Document):
    file_id: str = Field(..., description="Target file ID")
    job_type: str = Field(..., description="Processing job type")
    status: str = Field("pending", description="Job status")
    priority: int = Field(1, ge=1, le=10, description="Job priority")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing result")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(0, description="Number of retries")
    max_retries: int = Field(3, description="Maximum retry attempts")
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    model_config = ConfigDict(extra="forbid")

    class Settings:
        name = "file_processing_jobs"
        indexes = [
            IndexModel([("file_id", ASCENDING)], name="file_id"),
            IndexModel([("job_type", ASCENDING)], name="job_type"),
            IndexModel([("status", ASCENDING)], name="status"),
            IndexModel([("priority", ASCENDING)], name="priority"),
            IndexModel([("created_at", ASCENDING)], name="created_at"),
        ]

class FileVersion(Document):
    file_id: str = Field(..., description="Base file ID")
    version: int = Field(..., ge=1, description="Version number")
    filename: str = Field(..., description="Version filename")
    file_size: int = Field(..., description="Version file size")
    minio_object_name: str = Field(..., description="MinIO object name for this version")
    minio_etag: Optional[str] = Field(None, description="MinIO ETag")
    description: Optional[str] = Field(None, description="Version description")
    changes: List[str] = Field(default_factory=list, description="List of changes")
    created_at: datetime = Field(default_factory=get_current_time, description="Creation timestamp")
    created_by: str = Field(..., description="User ID who created this version")

    model_config = ConfigDict(extra="forbid")

    class Settings:
        name = "file_versions"
        indexes = [
            IndexModel([("file_id", ASCENDING)], name="file_id"),
            IndexModel([("version", ASCENDING)], name="version"),
            IndexModel([("created_at", ASCENDING)], name="created_at"),
        ]

# Expanded file type extensions
FILE_TYPE_EXTENSIONS = {
    FileType.PDF: ['.pdf'],
    FileType.DOCUMENT: ['.doc', '.docx', '.odt', '.rtf', '.docm'],
    FileType.SPREADSHEET: ['.xls', '.xlsx', '.ods', '.csv', '.xlsm'],
    FileType.PRESENTATION: ['.ppt', '.pptx', '.odp', '.pptm'],
    FileType.TEXT: ['.txt', '.md', '.markdown', '.log'],
    FileType.CODE: ['.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css', '.php', '.rb', '.go', '.ts'],
    FileType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'],
    FileType.VECTOR: ['.svg', '.ai', '.eps'],
    FileType.AUDIO: ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma'],
    FileType.VIDEO: ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
    FileType.JSON: ['.json'],
    FileType.XML: ['.xml', '.rss', '.atom'],
    FileType.CSV: ['.csv'],
    FileType.ARCHIVE: ['.zip', '.rar', '.tar', '.gz', '.7z', '.bz2', '.tar.gz'],
}

EXTENSION_FILE_TYPES = {
    ext: file_type
    for file_type, extensions in FILE_TYPE_EXTENSIONS.items()
    for ext in extensions
}