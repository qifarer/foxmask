# foxmask/file/graphql/__init__.py
from .schemas import (
    FileType, FileChunkType, FileCreateInput, FileUpdateInput,
    UploadProgress, MultipartUploadResult, ChunkUploadResult,
    ChunkEtagInput, ChunkUploadInput, CompleteUploadInput, Error,
    FileResponse, FileListResponse, FileChunkResponse, FileChunkListResponse,  # 添加 FileChunkResponse
    UploadProgressResponse, MultipartUploadResponse, ChunkUploadResponse,
    FileStatsResponse, PresignedUrlResponse, SuccessResponse
)
from .resolvers import FileQuery, FileMutation, file_to_gql, chunk_to_gql

__all__ = [
    'FileQuery', 'FileMutation', 'file_to_gql', 'chunk_to_gql',
    'FileType', 'FileChunkType', 'FileCreateInput', 'FileUpdateInput',
    'UploadProgress', 'MultipartUploadResult', 'ChunkUploadResult',
    'ChunkEtagInput', 'ChunkUploadInput', 'CompleteUploadInput', 'Error',
    'FileResponse', 'FileListResponse', 'FileChunkResponse', 'FileChunkListResponse',  # 添加 FileChunkResponse
    'UploadProgressResponse', 'MultipartUploadResponse', 'ChunkUploadResponse',
    'FileStatsResponse', 'PresignedUrlResponse', 'SuccessResponse'
]