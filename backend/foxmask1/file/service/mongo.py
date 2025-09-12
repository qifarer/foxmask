from typing import Optional, List
from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime

from foxmask.core.mongo import get_file_collection, get_kb_collection
from ..models.mongo import FileDocument, KnowledgeBaseDocument

class MongoService:
    def __init__(self):
        pass

    async def _get_file_collection(self):
        """获取文件集合（延迟加载）"""
        return await get_file_collection()

    async def _get_kb_collection(self):
        """获取知识库集合（延迟加载）"""
        return await get_kb_collection()

    async def create_file(self, file_data: FileDocument) -> FileDocument:
        """创建文件记录"""
        file_collection = await self._get_file_collection()
        file_dict = file_data.dict(by_alias=True, exclude={"id"})
        result = await file_collection.insert_one(file_dict)
        
        created_file = await file_collection.find_one({"_id": result.inserted_id})
        if created_file:
            created_file["_id"] = str(created_file["_id"])
            return FileDocument(**created_file)
        raise HTTPException(status_code=500, detail="Failed to create file")

    async def get_file_by_id(self, file_id: str) -> Optional[FileDocument]:
        """根据ID获取文件"""
        if not ObjectId.is_valid(file_id):
            return None
            
        file_collection = await self._get_file_collection()
        file_data = await file_collection.find_one({"_id": ObjectId(file_id)})
        if file_data:
            file_data["_id"] = str(file_data["_id"])
            return FileDocument(**file_data)
        return None

    async def get_file_by_hash(self, file_hash: str) -> Optional[FileDocument]:
        """根据哈希获取文件"""
        file_collection = await self._get_file_collection()
        file_data = await file_collection.find_one({"hash": file_hash})
        if file_data:
            file_data["_id"] = str(file_data["_id"])
            return FileDocument(**file_data)
        return None

    async def update_file(self, file_id: str, update_data: dict) -> Optional[FileDocument]:
        """更新文件"""
        if not ObjectId.is_valid(file_id):
            return None
            
        file_collection = await self._get_file_collection()
        update_data["updated_at"] = datetime.utcnow()
        result = await file_collection.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_file_by_id(file_id)
        return None

    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        if not ObjectId.is_valid(file_id):
            return False
            
        file_collection = await self._get_file_collection()
        result = await file_collection.delete_one({"_id": ObjectId(file_id)})
        return result.deleted_count > 0

    async def get_files_by_kb(self, kb_id: str) -> List[FileDocument]:
        """根据知识库ID获取文件"""
        file_collection = await self._get_file_collection()
        cursor = file_collection.find({"knowledge_base_id": kb_id})
        files = await cursor.to_list(length=1000)
        for file in files:
            file["_id"] = str(file["_id"])
        return [FileDocument(**file) for file in files]

    async def get_all_files(self, skip: int = 0, limit: int = 100) -> List[FileDocument]:
        """获取所有文件"""
        file_collection = await self._get_file_collection()
        cursor = file_collection.find().skip(skip).limit(limit)
        files = await cursor.to_list(length=limit)
        for file in files:
            file["_id"] = str(file["_id"])
        return [FileDocument(**file) for file in files]

    async def count_files(self) -> int:
        """统计文件总数"""
        file_collection = await self._get_file_collection()
        return await file_collection.count_documents({})

    async def create_knowledge_base(self, kb_data: KnowledgeBaseDocument) -> KnowledgeBaseDocument:
        """创建知识库"""
        kb_collection = await self._get_kb_collection()
        kb_dict = kb_data.dict(by_alias=True, exclude={"id"})
        result = await kb_collection.insert_one(kb_dict)
        
        created_kb = await kb_collection.find_one({"_id": result.inserted_id})
        if created_kb:
            created_kb["_id"] = str(created_kb["_id"])
            return KnowledgeBaseDocument(**created_kb)
        raise HTTPException(status_code=500, detail="Failed to create knowledge base")

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBaseDocument]:
        """获取知识库"""
        if not ObjectId.is_valid(kb_id):
            return None
            
        kb_collection = await self._get_kb_collection()
        kb_data = await kb_collection.find_one({"_id": ObjectId(kb_id)})
        if kb_data:
            kb_data["_id"] = str(kb_data["_id"])
            return KnowledgeBaseDocument(**kb_data)
        return None

    async def get_all_knowledge_bases(self) -> List[KnowledgeBaseDocument]:
        """获取所有知识库"""
        kb_collection = await self._get_kb_collection()
        cursor = kb_collection.find()
        kbs = await cursor.to_list(length=1000)
        for kb in kbs:
            kb["_id"] = str(kb["_id"])
        return [KnowledgeBaseDocument(**kb) for kb in kbs]

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库"""
        if not ObjectId.is_valid(kb_id):
            return False
            
        kb_collection = await self._get_kb_collection()
        result = await kb_collection.delete_one({"_id": ObjectId(kb_id)})
        return result.deleted_count > 0