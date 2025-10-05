# -*- coding: utf-8 -*-
# foxmask/file/exceptions.py
class UploadError(Exception):
    """Base exception for upload errors"""
    pass


class TaskNotFoundError(UploadError):
    """Raised when upload task is not found"""
    pass


class FileNotFoundError(UploadError):
    """Raised when task file is not found"""
    pass


class ChunkUploadFailedError(UploadError):
    """Raised when chunk upload fails after max retries"""
    pass