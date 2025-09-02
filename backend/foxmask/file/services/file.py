from fastapi import HTTPException
from typing import Optional, List
from datetime import datetime

from ..services.mongo import MongoService
from ..models.mongo import FileDocument
from ..models.file import FileCreateRequest, FileResponse, CheckFileHashResponse, FileListResponse

class FileService:
    def __init__(self, mongo_service: MongoService):
        self.mongo_service = mongo_service

    async def create_file(
        self, 
        file_data: FileCreateRequest, 
        knowledge_base_id: Optional[str] = None
    ) -> FileResponse:
        """创建文件记录到 MongoDB"""
        # 检查文件是否已存在
        existing_file = await self.mongo_service.get_file_by_hash(file_data.hash)
        if existing_file:
            return FileResponse(
                id=existing_file.id,
                name=existing_file.name,
                file_type=existing_file.file_type,
                hash=existing_file.hash,
                size=existing_file.size,
                url=existing_file.url,
                metadata=existing_file.metadata,
                created_at=existing_file.created_at,
                updated_at=existing_file.updated_at
            )
        
        # 创建新文件记录
        mongo_file = FileDocument(
            name=file_data.name,
            file_type=file_data.file_type,
            hash=file_data.hash,
            size=file_data.size,
            url=file_data.url,
            metadata=file_data.metadata.model_dump(),
            knowledge_base_id=knowledge_base_id
        )
      
        created_file = await self.mongo_service.create_file(mongo_file)
        
        return FileResponse(
            id=str(mongo_file.id),
            name=created_file.name,
            file_type=created_file.file_type,
            hash=created_file.hash,
            size=created_file.size,
            url=created_file.url,
            metadata=created_file.metadata.model_dump(),
            created_at=created_file.created_at,
            updated_at=created_file.updated_at
        )

    async def check_file_hash(self, file_hash: str) -> CheckFileHashResponse:
        """检查文件哈希是否已存在"""
        existing_file = await self.mongo_service.get_file_by_hash(file_hash)
        
        if existing_file:
            return CheckFileHashResponse(
                is_exist=True,
                metadata=existing_file.metadata,
                url=existing_file.url
            )
        
        return CheckFileHashResponse(is_exist=False)

    async def get_file_by_id(self, file_id: str) -> FileResponse:
        """根据ID获取文件"""
        db_file = await self.mongo_service.get_file_by_id(file_id)
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            id=db_file.id,
            name=db_file.name,
            file_type=db_file.file_type,
            hash=db_file.hash,
            size=db_file.size,
            url=db_file.url,
            metadata=db_file.metadata,
            created_at=db_file.created_at,
            updated_at=db_file.updated_at
        )

    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        return await self.mongo_service.delete_file(file_id)

    async def get_files_by_knowledge_base(self, kb_id: str) -> List[FileResponse]:
        """根据知识库ID获取文件"""
        files = await self.mongo_service.get_files_by_kb(kb_id)
        return [
            FileResponse(
                id=file.id,
                name=file.name,
                file_type=file.file_type,
                hash=file.hash,
                size=file.size,
                url=file.url,
                metadata=file.metadata,
                created_at=file.created_at,
                updated_at=file.updated_at
            )
            for file in files
        ]

    async def get_all_files(self, skip: int = 0, limit: int = 100) -> FileListResponse:
        """获取所有文件"""
        files = await self.mongo_service.get_all_files(skip, limit)
        total = await self.mongo_service.count_files()
        
        file_responses = [
            FileResponse(
                id=file.id,
                name=file.name,
                file_type=file.file_type,
                hash=file.hash,
                size=file.size,
                url=file.url,
                metadata=file.metadata,
                created_at=file.created_at,
                updated_at=file.updated_at
            )
            for file in files
        ]
        
        return FileListResponse(
            files=file_responses,
            total=total,
            skip=skip,
            limit=limit
        )
    
file_service = FileService(mongo_service=MongoService())    