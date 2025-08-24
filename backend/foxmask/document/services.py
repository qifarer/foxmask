# foxmask/document/services.py (增强版)
from typing import List, Optional, Dict, Any
from datetime import datetime
from foxmask.core.database import get_database
from foxmask.core.kafka import get_kafka_producer
from foxmask.core.exceptions import NotFoundError
from foxmask.document.models import Document, DocumentStatus
from foxmask.core.config import get_settings
from foxmask.core.tracking import tracking_service, track_performance
from foxmask.auth.schemas import User

settings = get_settings()

class DocumentService:
    def __init__(self):
        self.db = get_database()
        self.producer = get_kafka_producer()
    
    @track_performance("document_create")
    async def create_document(
        self, 
        title: str, 
        description: str, 
        file_ids: List[str], 
        owner: str,
        user: User,
        metadata: Dict[str, Any] = None
    ) -> Document:
        document = Document(
            title=title,
            description=description,
            file_ids=file_ids,
            owner=owner,
            metadata=metadata or {}
        )
        
        await self.db.documents.insert_one(document.dict())
        
        # Send Kafka message for document processing
        self.producer.send(settings.KAFKA_TOPIC_DOCUMENT_CREATED, {
            "document_id": document.id,
            "file_ids": file_ids,
            "owner": owner,
            "metadata": metadata or {}
        })
        
        # Update status to created
        document.status = DocumentStatus.CREATED
        await self.db.documents.update_one(
            {"id": document.id},
            {"$set": {"status": DocumentStatus.CREATED, "updated_at": datetime.utcnow()}}
        )
        
        # 记录文档创建事件
        await tracking_service.log_document_operation(
            operation="create",
            document_id=document.id,
            title=title,
            user=user,
            details={
                "file_count": len(file_ids),
                "status": document.status
            }
        )
        
        return document
    
    @track_performance("document_get")
    async def get_document(self, document_id: str, owner: str) -> Optional[Document]:
        data = await self.db.documents.find_one({"id": document_id, "owner": owner})
        if data:
            return Document(**data)
        return None
    
    @track_performance("document_list")
    async def list_documents(
        self, 
        owner: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[DocumentStatus] = None
    ) -> List[Document]:
        query = {"owner": owner}
        if status:
            query["status"] = status
            
        cursor = self.db.documents.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [Document(**doc) async for doc in cursor]
    
    @track_performance("document_update_status")
    async def update_status(
        self, 
        document_id: str, 
        status: DocumentStatus, 
        owner: str,
        user: User
    ) -> Document:
        document = await self.get_document(document_id, owner)
        if not document:
            raise NotFoundError("Document not found")
        
        document.status = status
        document.updated_at = datetime.utcnow()
        
        await self.db.documents.update_one(
            {"id": document_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        
        # 记录文档状态更新事件
        await tracking_service.log_document_operation(
            operation="update_status",
            document_id=document_id,
            title=document.title,
            user=user,
            details={
                "old_status": document.status,
                "new_status": status
            }
        )
        
        return document
    
    @track_performance("document_update_processed_files")
    async def update_processed_files(
        self, 
        document_id: str, 
        processed_file_ids: List[str], 
        owner: str,
        user: User
    ) -> Document:
        document = await self.get_document(document_id, owner)
        if not document:
            raise NotFoundError("Document not found")
        
        document.processed_file_ids = processed_file_ids
        document.updated_at = datetime.utcnow()
        
        await self.db.documents.update_one(
            {"id": document_id},
            {"$set": {
                "processed_file_ids": processed_file_ids,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # 记录文档处理文件更新事件
        await tracking_service.log_document_operation(
            operation="update_processed_files",
            document_id=document_id,
            title=document.title,
            user=user,
            details={
                "processed_file_count": len(processed_file_ids)
            }
        )
        
        return document
    
    @track_performance("document_delete")
    async def delete_document(self, document_id: str, owner: str, user: User):
        document = await self.get_document(document_id, owner)
        if not document:
            raise NotFoundError("Document not found")
        
        await self.db.documents.delete_one({"id": document_id, "owner": owner})
        
        # 记录文档删除事件
        await tracking_service.log_document_operation(
            operation="delete",
            document_id=document_id,
            title=document.title,
            user=user,
            details={
                "file_count": len(document.file_ids),
                "status": document.status
            }
        )
        
        # TODO: Optionally delete associated files