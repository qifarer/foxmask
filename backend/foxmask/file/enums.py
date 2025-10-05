from enum import Enum

class FileTypeEnum(str, Enum):
    """文件类型枚举"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    CODE = "code"
    DATA = "data"
    OTHER = "other"

class UploadProcStatusEnum(str, Enum):
    """文件状态枚举"""
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
    RETRYING = "retrying"


class UploadTaskTypeEnum(str, Enum):
    """上传任务类型"""
    SINGLE_FILE = "single_file"
    MULTIPLE_FILES = "multiple_files"
    SINGLE_DIRECTORY = "single_directory"
    MULTIPLE_DIRECTORIES = "multiple_directories"
    
class FileSortFieldEnum(str, Enum):
    """文件排序字段"""
    FILENAME = "filename"
    FILE_SIZE = "file_size"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    UPLOADED_AT = "uploaded_at"

class SortOrderEnum(str, Enum):
    """排序顺序"""
    ASC = "asc"
    DESC = "desc"

class FileOperationTypeEnum(str, Enum):
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

class UploadSourceTypeEnum(str, Enum):
    """上传源类型"""
    SINGLE_FILE = "single_file"
    MULTIPLE_FILES = "multiple_files" 
    SINGLE_DIRECTORY = "single_directory"
    MULTIPLE_DIRECTORIES = "multiple_directories"

class UploadStrategyEnum(str, Enum):
    """上传策略"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    STREAMING = "streaming"