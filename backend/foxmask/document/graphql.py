# foxmask/document/graphql.py
import strawberry
from typing import List, Optional
from foxmask.document.models import Document, DocumentStatus
from foxmask.document.services import DocumentService
from foxmask.auth.dependencies import get_current_user

@strawberry.type
class Document:
    id: strawberry.ID
    title: str
    description: str
    status: str
    file_ids: List[str]
    processed_file_ids: Optional[List[str]] = None
    owner: str
    created_at: str
    updated_at: str

@strawberry.input
class CreateDocumentInput:
    title: str
    description: str
    file_ids: List[str]

@strawberry.type
class DocumentMutation:
    @strawberry.mutation
    async def create_document(self, info, input: CreateDocumentInput) -> Document:
        user = await get_current_user(info.context["request"])
        service = DocumentService()
        document = await service.create_document(
            input.title,
            input.description,
            input.file_ids,
            user.id
        )
        return Document(**document.dict())

@strawberry.type
class DocumentQuery:
    @strawberry.field
    async def documents(self, info) -> List[Document]:
        user = await get_current_user(info.context["request"])
        service = DocumentService()
        documents = await service.list_documents(user.id)
        return [Document(**doc.dict()) for doc in documents]