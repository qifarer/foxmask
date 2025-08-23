# app/core/exceptions.py
from fastapi import HTTPException, status

class FoxmaskException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundError(FoxmaskException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)

class PermissionDeniedError(FoxmaskException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(detail, status_code=status.HTTP_403_FORBIDDEN)

class ValidationError(FoxmaskException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class ServiceError(FoxmaskException):
    def __init__(self, detail: str = "Service error"):
        super().__init__(detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AuthenticationError(FoxmaskException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail, 
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )