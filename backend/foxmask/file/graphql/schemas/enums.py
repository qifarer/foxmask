import strawberry
from enum import Enum


@strawberry.enum
class FileTypeGql(str, Enum):
    """文件类型枚举"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    CODE = "code"
    DATA = "data"
    OTHER = "other"


@strawberry.enum
class UploadProcStatusGql(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING= "processing"
    UPLOADED = "uploaded"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DELETED = "deleted"

@strawberry.enum
class FileSortFieldGql(str, Enum):
    """文件排序字段"""
    FILENAME = "filename"
    FILE_SIZE = "file_size"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    UPLOADED_AT = "uploaded_at"


@strawberry.enum
class SortOrderGql(str, Enum):
    """排序顺序"""
    ASC = "asc"
    DESC = "desc"


@strawberry.enum
class FileOperationTypeGql(str, Enum):
    """文件操作类型"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    UPDATE = "update"
    DELETE = "delete"
    SHARE = "share"
    PREVIEW = "preview"
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"


@strawberry.enum
class UploadSourceTypeGql(str, Enum):
    """上传源类型"""
    SINGLE_FILE = "single_file"
    MULTIPLE_FILES = "multiple_files"
    SINGLE_DIRECTORY = "single_directory"
    MULTIPLE_DIRECTORIES = "multiple_directories"


@strawberry.enum
class UploadStrategyGql(str, Enum):
    """上传策略"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    STREAMING = "streaming"


@strawberry.enum
class VisibilityGql(str, Enum):
    """可见性枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"


@strawberry.enum
class StatusGql(str, Enum):
    """状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"