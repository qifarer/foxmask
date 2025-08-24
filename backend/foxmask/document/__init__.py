# foxmask/document/__init__.py
from .models import Document, DocumentStatus
from .schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from .services import DocumentService
from .routers import router
from .graphql import Document, CreateDocumentInput, DocumentMutation, DocumentQuery

__all__ = [
    'Document',
    'DocumentStatus',
    'DocumentCreate',
    'DocumentResponse',
    'DocumentUpdate',
    'DocumentService',
    'router',
    'Document',
    'CreateDocumentInput',
    'DocumentMutation',
    'DocumentQuery'
]