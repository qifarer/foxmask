# app/domains/task/consumers.py
import asyncio
import json
from foxmask.core.kafka import KafkaConsumer
from foxmask.core.database import get_database
from foxmask.core.minio import get_minio_client
from foxmask.document.services import DocumentService
from foxmask.file.services import FileService
from foxmask.task.services import TaskService
from foxmask.core.config import get_settings
from foxmask.task.models import TaskType, TaskStatus
from foxmask.document.models import DocumentStatus

settings = get_settings()

class DocumentConsumer:
    def __init__(self):
        self.db = get_database()
        self.minio_client = get_minio_client()
        self.document_service = DocumentService()
        self.file_service = FileService()
        self.task_service = TaskService()
        
        self.consumer = KafkaConsumer(
            settings.KAFKA_TOPIC_DOCUMENT_CREATED,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='document-processors',
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )
    
    async def start_consuming(self):
        print("Starting document consumer...")
        for message in self.consumer:
            try:
                data = message.value
                await self.process_document(data)
                self.consumer.commit()
            except Exception as e:
                print(f"Error processing message: {e}")
                # Implement retry logic or dead letter queue
    
    async def process_document(self, data: dict):
        document_id = data['document_id']
        file_ids = data['file_ids']
        owner = data['owner']
        metadata = data.get('metadata', {})
        
        # Create parsing task
        task = await self.task_service.create_task(
            TaskType.DOCUMENT_PARSING,
            document_id,
            owner,
            {"file_ids": file_ids, "metadata": metadata}
        )
        
        try:
            # Update document status to parsing
            await self.document_service.update_status(
                document_id, 
                DocumentStatus.PARSING, 
                owner
            )
            
            # Update task status to processing
            await self.task_service.update_task_status(
                task.id, 
                TaskStatus.PROCESSING
            )
            
            # Process files (convert PDF to MD/JSON)
            processed_files = []
            for file_id in file_ids:
                processed_file = await self._process_file(file_id, owner)
                processed_files.append(processed_file)
            
            # Update document with processed files
            await self.document_service.update_processed_files(
                document_id,
                [pf['id'] for pf in processed_files],
                owner
            )
            
            # Update document status to parsed
            await self.document_service.update_status(
                document_id, 
                DocumentStatus.PARSED, 
                owner
            )
            
            # Update task status to completed
            await self.task_service.update_task_status(
                task.id, 
                TaskStatus.COMPLETED,
                {"processed_files": processed_files}
            )
            
            # Send message for vectorization
            from foxmask.core.kafka import get_kafka_producer
            producer = get_kafka_producer()
            producer.send(settings.KAFKA_TOPIC_DOCUMENT_PARSED, {
                "document_id": document_id,
                "processed_file_ids": [pf['id'] for pf in processed_files],
                "owner": owner,
                "metadata": metadata
            })
            
        except Exception as e:
            # Update task status to failed
            await self.task_service.update_task_status(
                task.id, 
                TaskStatus.FAILED,
                error=str(e)
            )
            
            # Revert document status
            await self.document_service.update_status(
                document_id, 
                DocumentStatus.CREATED, 
                owner
            )
    
    async def _process_file(self, file_id: str, owner: str) -> dict:
        # Implement actual file processing logic
        # This would include PDF parsing, text extraction, etc.
        # For now, return a mock processed file
        return {
            "id": f"processed_{file_id}",
            "format": "md",
            "size": 1024,
            "content_type": "text/markdown"
        }