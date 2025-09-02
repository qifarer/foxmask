# foxmask/document/services.py
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from foxmask.core.mongo import get_docs_collection, get_files_collection, get_contents_collection, get_relations_collection
from foxmask.core.kafka import get_kafka_producer
from foxmask.core.exceptions import NotFoundError, ServiceError
from foxmask.document.models import Document, Content, File, DocumentFileRelation, DocumentStatus, ContentStatus, FileStatus
from foxmask.document.schemas import DocumentCreate, ContentCreate, FileCreate
from foxmask.core.config import get_settings
from foxmask.core.tracking import tracking_service, track_performance
from foxmask.auth.schemas import User

logger = logging.getLogger(__name__)
settings = get_settings()

class DocumentService:
    def __init__(self):
        self.docs_collection = get_docs_collection()
        self.files_collection = get_files_collection()
        self.contents_collection = get_contents_collection()
        self.relations_collection = get_relations_collection()
        self.producer = get_kafka_producer()
        logger.info("DocumentService initialized")
    
    @track_performance("document_create")
    async def create_document(
        self, 
        document_data: DocumentCreate,
        owner: str,
        user: User
    ) -> Document:
        """创建文档并发送文档解析消息"""
        try:
            logger.info(f"Creating document: {document_data.title} for owner: {owner}")
            
            # 转换schema到model
            document = Document(
                title=document_data.title,
                description=document_data.description,
                source_type=document_data.source_type,
                source_details=document_data.source_details,
                file_ids=document_data.file_ids,
                owner=owner,
                metadata=document_data.metadata or {},
                tags=document_data.tags or [],
                status=DocumentStatus.CREATED
            )
            
            # 插入文档到数据库
            await self.docs_collection.insert_one(document.model_dump())
            logger.debug(f"Document inserted to MongoDB: {document.id}")
            
            # 发送Kafka消息进行文档解析
            try:
                kafka_message = {
                    "document_id": str(document.id),
                    "file_ids": document_data.file_ids,
                    "owner": owner,
                    "source_type": document_data.source_type.value,
                    "metadata": document_data.metadata or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if document_data.source_details:
                    kafka_message["source_details"] = document_data.source_details.model_dump()
                
                self.producer.send(
                    settings.KAFKA_TOPIC_DOCUMENT_CREATED, 
                    kafka_message
                )
                logger.info(f"Sent document processing message to Kafka: {document.id}")
                
            except Exception as kafka_error:
                logger.error(f"Failed to send Kafka message for document {document.id}: {kafka_error}")
                document.status = DocumentStatus.ERROR
                document.error_message = f"Kafka error: {kafka_error}"
                await self.docs_collection.update_one(
                    {"id": document.id},
                    {"$set": {"status": DocumentStatus.ERROR, "error_message": document.error_message, "updated_at": datetime.utcnow()}}
                )
                raise ServiceError(f"Failed to send processing message: {kafka_error}")
            
            # 记录文档创建事件
            await tracking_service.log_document_operation(
                operation="create",
                document_id=document.id,
                title=document_data.title,
                user=user,
                details={
                    "file_count": len(document_data.file_ids),
                    "status": document.status.value,
                    "source_type": document_data.source_type.value,
                    "kafka_message_sent": True
                }
            )
            
            logger.info(f"Document created successfully: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to create document {document_data.title}: {e}")
            raise ServiceError(f"Document creation failed: {e}")
    
    @track_performance("document_get")
    async def get_document(self, document_id: str, owner: str) -> Optional[Document]:
        """获取单个文档"""
        try:
            logger.debug(f"Fetching document: {document_id} for owner: {owner}")
            data = await self.docs_collection.find_one({"id": document_id, "owner": owner})
            
            if data:
                logger.debug(f"Document found: {document_id}")
                return Document(**data)
            
            logger.warning(f"Document not found: {document_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}")
            raise ServiceError(f"Failed to fetch document: {e}")
    
    @track_performance("document_list")
    async def list_documents(
        self, 
        owner: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        source_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Document]:
        """列出用户的文档"""
        try:
            logger.debug(f"Listing documents for owner: {owner}")
            
            query = {"owner": owner}
            if status:
                query["status"] = status.value
            if source_type:
                query["source_type"] = source_type
            if tags:
                query["tags"] = {"$in": tags}
                
            cursor = self.docs_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            documents = [Document(**doc) async for doc in cursor]
            
            logger.debug(f"Found {len(documents)} documents for owner: {owner}")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents for owner {owner}: {e}")
            raise ServiceError(f"Failed to list documents: {e}")
    
    @track_performance("document_update_status")
    async def update_status(
        self, 
        document_id: str, 
        status: DocumentStatus, 
        owner: str,
        user: User,
        processing_details: Optional[Dict[str, Any]] = None
    ) -> Document:
        """更新文档状态，并在解析完成后发送向量处理消息"""
        try:
            logger.info(f"Updating status for document: {document_id} to {status}")
            
            document = await self.get_document(document_id, owner)
            if not document:
                raise NotFoundError("Document not found")
            
            old_status = document.status
            document.status = status
            document.updated_at = datetime.utcnow()
            
            # 更新数据库
            update_data = {
                "status": status.value, 
                "updated_at": datetime.utcnow()
            }
            
            if processing_details:
                update_data["processing_stats"] = processing_details
            
            await self.docs_collection.update_one(
                {"id": document_id},
                {"$set": update_data}
            )
            
            # 如果文档解析完成，发送向量处理消息
            if status == DocumentStatus.PROCESSED:
                try:
                    vector_message = {
                        "document_id": str(document_id),
                        "file_ids": document.file_ids,
                        "owner": owner,
                        "source_type": document.source_type.value,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    self.producer.send(
                        settings.KAFKA_TOPIC_VECTOR_PROCESSING, 
                        vector_message
                    )
                    logger.info(f"Sent vector processing message for document: {document_id}")
                    
                except Exception as kafka_error:
                    logger.error(f"Failed to send vector processing message for document {document_id}: {kafka_error}")
                    document.status = DocumentStatus.ERROR
                    document.error_message = f"Vector processing error: {kafka_error}"
                    await self.docs_collection.update_one(
                        {"id": document_id},
                        {"$set": {"status": DocumentStatus.ERROR, "error_message": document.error_message, "updated_at": datetime.utcnow()}}
                    )
                    raise ServiceError(f"Failed to send vector processing message: {kafka_error}")
            
            # 记录文档状态更新事件
            await tracking_service.log_document_operation(
                operation="update_status",
                document_id=document_id,
                title=document.title,
                user=user,
                details={
                    "old_status": old_status.value,
                    "new_status": status.value,
                    "vector_message_sent": status == DocumentStatus.PROCESSED
                }
            )
            
            logger.info(f"Status updated successfully for document: {document_id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to update status for document {document_id}: {e}")
            raise ServiceError(f"Status update failed: {e}")
    
    @track_performance("document_delete")
    async def delete_document(self, document_id: str, owner: str, user: User):
        """删除文档"""
        try:
            logger.info(f"Deleting document: {document_id} for owner: {owner}")
            
            document = await self.get_document(document_id, owner)
            if not document:
                raise NotFoundError("Document not found")
            
            await self.docs_collection.delete_one({"id": document_id, "owner": owner})
            
            # 记录文档删除事件
            await tracking_service.log_document_operation(
                operation="delete",
                document_id=document_id,
                title=document.title,
                user=user,
                details={
                    "file_count": len(document.file_ids),
                    "status": document.status.value,
                    "source_type": document.source_type.value
                }
            )
            
            # 发送文档删除消息到Kafka
            try:
                delete_message = {
                    "document_id": str(document_id),
                    "owner": owner,
                    "file_ids": document.file_ids,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                self.producer.send(
                    settings.KAFKA_TOPIC_DOCUMENT_DELETED, 
                    delete_message
                )
                logger.info(f"Sent document deletion message to Kafka: {document_id}")
                
            except Exception as kafka_error:
                logger.warning(f"Failed to send deletion message for document {document_id}: {kafka_error}")
            
            logger.info(f"Document deleted successfully: {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise ServiceError(f"Document deletion failed: {e}")
    
    # 文件相关方法
    @track_performance("file_create")
    async def create_file(self, file_data: FileCreate, owner: str) -> File:
        """创建文件记录"""
        try:
            file = File(
                name=file_data.name,
                original_name=file_data.original_name,
                size=file_data.size,
                mime_type=file_data.mime_type,
                storage_path=file_data.storage_path,
                owner=owner,
                metadata=file_data.metadata or {},
                status=FileStatus.UPLOADED
            )
            
            await self.files_collection.insert_one(file.model_dump())
            logger.info(f"File created: {file.id}")
            return file
            
        except Exception as e:
            logger.error(f"Failed to create file: {e}")
            raise ServiceError(f"File creation failed: {e}")
    
    @track_performance("file_get")
    async def get_file(self, file_id: str, owner: str) -> Optional[File]:
        """获取文件记录"""
        data = await self.files_collection.find_one({"id": file_id, "owner": owner})
        return File(**data) if data else None
    
    # 内容相关方法
    @track_performance("content_create")
    async def create_content(self, content_data: ContentCreate) -> Content:
        """创建内容记录"""
        try:
            content = Content(
                document_id=content_data.document_id,
                raw_text=content_data.raw_text,
                structured_data=content_data.structured_data,
                metadata=content_data.metadata or {},
                status=ContentStatus.PARSED
            )
            
            await self.contents_collection.insert_one(content.model_dump())
            logger.info(f"Content created for document: {content_data.document_id}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to create content: {e}")
            raise ServiceError(f"Content creation failed: {e}")
    
    @track_performance("content_get")
    async def get_content(self, content_id: str) -> Optional[Content]:
        """获取内容记录"""
        data = await self.contents_collection.find_one({"id": content_id})
        return Content(**data) if data else None
    
    @track_performance("content_get_by_document")
    async def get_content_by_document(self, document_id: str) -> Optional[Content]:
        """通过文档ID获取内容"""
        data = await self.contents_collection.find_one({"document_id": document_id})
        return Content(**data) if data else None