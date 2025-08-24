# foxmask/document/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.schemas import User
from foxmask.document.services import DocumentService
from foxmask.document.schemas import DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user)
):
    service = DocumentService()
    try:
        new_document = await service.create_document(
            document.title,
            document.description,
            document.file_ids,
            current_user.id,
            document.metadata
        )
        return new_document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    service = DocumentService()
    documents = await service.list_documents(
        current_user.id, 
        skip, 
        limit,
        DocumentStatus(status) if status else None
    )
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    service = DocumentService()
    document = await service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user)
):
    service = DocumentService()
    # Implement update logic based on the fields in document_update
    # This is a simplified implementation
    document = await service.get_document(document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update logic would go here
    return document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    service = DocumentService()
    await service.delete_document(document_id, current_user.id)
    return None