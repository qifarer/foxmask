# foxmask/document/graphql.py
import strawberry
from typing import List, Optional
from foxmask.document.models import Document, DocumentStatus, DocumentSourceType
from foxmask.document.services import DocumentService
from foxmask.auth.dependencies import get_current_user
from foxmask.document.schemas import DocumentCreate
from foxmask.auth.schemas import User

@strawberry.type
class WebSourceDetails:
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    fetched_at: Optional[str] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None

@strawberry.type
class ApiSourceDetails:
    endpoint: str
    api_name: str
    parameters: Optional[str] = None
    response_format: Optional[str] = None

@strawberry.type
class FileSourceDetails:
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    storage_path: Optional[str] = None

@strawberry.type
class TextSourceDetails:
    content: str
    language: Optional[str] = None

@strawberry.type
class DocumentType:
    id: strawberry.ID
    title: str
    description: Optional[str] = None
    status: str
    source_type: str
    source_uri: Optional[str] = None
    file_ids: List[str]
    processed_file_ids: Optional[List[str]] = None
    owner: str
    created_at: str
    updated_at: str
    tags: List[str]

@strawberry.input
class CreateDocumentInput:
    title: str
    description: str
    source_type: str
    file_ids: List[str]
    metadata: Optional[str] = None
    tags: Optional[List[str]] = None

@strawberry.input
class DocumentFilterInput:
    status: Optional[str] = None
    source_type: Optional[str] = None
    tags: Optional[List[str]] = None

@strawberry.type
class DocumentMutation:
    @strawberry.mutation
    async def create_document(self, info, input: CreateDocumentInput) -> DocumentType:
        user = await get_current_user(info.context["request"])
        service = DocumentService()
        
        # 转换输入到DocumentCreate schema
        document_data = DocumentCreate(
            title=input.title,
            description=input.description,
            source_type=DocumentSourceType(input.source_type),
            file_ids=input.file_ids,
            metadata={} if not input.metadata else eval(input.metadata),
            tags=input.tags or []
        )
        
        document = await service.create_document(
            document_data,
            user.id,
            user
        )
        
        return DocumentType(
            id=document.id,
            title=document.title,
            description=document.description,
            status=document.status.value,
            source_type=document.source_type.value,
            source_uri=document.source_uri,
            file_ids=document.file_ids,
            processed_file_ids=document.processed_file_ids,
            owner=document.owner,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            tags=document.tags
        )

@strawberry.type
class DocumentQuery:
    @strawberry.field
    async def documents(
        self, 
        info,
        skip: int = 0,
        limit: int = 100,
        filter: Optional[DocumentFilterInput] = None
    ) -> List[DocumentType]:
        user = await get_current_user(info.context["request"])
        service = DocumentService()
        
        status_filter = DocumentStatus(filter.status) if filter and filter.status else None
        source_type_filter = DocumentSourceType(filter.source_type) if filter and filter.source_type else None
        tags_filter = filter.tags if filter and filter.tags else None
        
        documents = await service.list_documents(
            user.id, 
            skip, 
            limit,
            status_filter,
            source_type_filter.value if source_type_filter else None,
            tags_filter
        )
        
        return [
            DocumentType(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                status=doc.status.value,
                source_type=doc.source_type.value,
                source_uri=doc.source_uri,
                file_ids=doc.file_ids,
                processed_file_ids=doc.processed_file_ids,
                owner=doc.owner,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
                tags=doc.tags
            )
            for doc in documents
        ]
    
    @strawberry.field
    async def document(self, info, id: strawberry.ID) -> Optional[DocumentType]:
        user = await get_current_user(info.context["request"])
        service = DocumentService()
        
        document = await service.get_document(str(id), user.id)
        if not document:
            return None
        
        return DocumentType(
            id=document.id,
            title=document.title,
            description=document.description,
            status=document.status.value,
            source_type=document.source_type.value,
            source_uri=document.source_uri,
            file_ids=document.file_ids,
            processed_file_ids=document.processed_file_ids,
            owner=document.owner,
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
            tags=document.tags
        )

# GraphQL Schema
document_schema = strawberry.Schema(
    query=DocumentQuery,
    mutation=DocumentMutation
)