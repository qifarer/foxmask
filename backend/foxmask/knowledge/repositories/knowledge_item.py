# foxmask/knowledge/repositories/knowledge_item_repository.py
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from beanie.operators import In, Eq, And

from foxmask.knowledge.models import (
    KnowledgeItem, KnowledgeItemInfo, KnowledgeItemChunk,
    KnowledgeItemTypeEnum, ItemChunkTypeEnum
)

from foxmask.core.model import Status, Visibility
from foxmask.core.exceptions import (
    DatabaseException, NotFoundException, DuplicateException
)

class KnowledgeItemRepository:
    
    @staticmethod
    async def get_by_id(id: PydanticObjectId) -> Optional[KnowledgeItem]:
        """根据ID获取知识条目"""
        try:
            item = await KnowledgeItem.get(id)
            return item
        except ValueError as e:
            raise DatabaseException(f"Invalid ID format: {str(e)}")
        except Exception as e:
            raise DatabaseException(f"Failed to get knowledge item by ID {id}: {str(e)}")
    
    @staticmethod
    async def get_by_source_id(source_id: str, tenant_id: str) -> Optional[KnowledgeItem]:
        """根据源ID获取知识条目"""
        try:
            item = await KnowledgeItem.find_one(
                KnowledgeItem.source_id == source_id, 
                KnowledgeItem.tenant_id == tenant_id
            )
            return item
        except Exception as e:
            raise DatabaseException(f"Failed to get knowledge item by source ID {source_id}: {str(e)}")
    
    @staticmethod
    async def get_by_uid(uid: str, tenant_id: str) -> Optional[KnowledgeItem]:
        """根据UID获取知识条目"""
        try:
            
            item = await KnowledgeItem.find_one(
                KnowledgeItem.uid == uid, 
                KnowledgeItem.tenant_id == tenant_id

            )
            return item
        except Exception as e:
            raise DatabaseException(f"Failed to get knowledge item by UID {uid}: {str(e)}")
    
    @staticmethod
    async def create(item: KnowledgeItem) -> KnowledgeItem:
        """创建知识条目"""
        try:
            # 检查是否已存在
            existing = await KnowledgeItem.find_one(
                KnowledgeItem.uid == item.uid,
                KnowledgeItem.tenant_id == item.tenant_id
            )
            if existing:
                raise DuplicateException("KnowledgeItem", item.uid)
            
            created_item = await item.create()
            return created_item
        except DuplicateException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to create knowledge item {item.uid}: {str(e)}")
    
    @staticmethod
    async def update(id: PydanticObjectId, update_data: Dict[str, Any]) -> Optional[KnowledgeItem]:
        """更新知识条目"""
        try:
            item = await KnowledgeItem.get(id)
            if not item:
                return None
            
            await item.set(update_data)
            return item
        except Exception as e:
            raise DatabaseException(f"Failed to update knowledge item {id}: {str(e)}")
    
    @staticmethod
    async def delete(id: PydanticObjectId) -> bool:
        """删除知识条目"""
        try:
            item = await KnowledgeItem.get(id)
            if not item:
                return False
            
            await item.delete()
            return True
        except Exception as e:
            raise DatabaseException(f"Failed to delete knowledge item {id}: {str(e)}")
    
    @staticmethod
    async def find(
        tenant_id: str,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[Status] = None,
        visibility: Optional[Visibility] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItem]:
        """查询知识条目"""
        try:
            query = [KnowledgeItem.tenant_id == tenant_id]
            
            if item_type:
                query.append(KnowledgeItem.item_type == item_type)
            if status:
                query.append(KnowledgeItem.status == status)
            if visibility:
                query.append(KnowledgeItem.visibility == visibility)
            if created_by:
                query.append(KnowledgeItem.created_by == created_by)
            if tags:
                query.append(In(KnowledgeItem.tags, tags))
            
            items = await KnowledgeItem.find(And(*query)).skip(skip).limit(limit).to_list()
            return items
        except Exception as e:
            raise DatabaseException(f"Failed to find knowledge items: {str(e)}")
    
    @staticmethod
    async def count(
        tenant_id: str,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[Status] = None
    ) -> int:
        """统计知识条目数量"""
        try:
            query = [KnowledgeItem.tenant_id == tenant_id]
            
            if item_type:
                query.append(KnowledgeItem.item_type == item_type)
            if status:
                query.append(KnowledgeItem.status == status)
                
            count = await KnowledgeItem.find(And(*query)).count()
            return count
        except Exception as e:
            raise DatabaseException(f"Failed to count knowledge items: {str(e)}")

    @staticmethod
    async def delete_with_related_data(item_id: PydanticObjectId) -> bool:
        """删除知识条目及相关数据"""
        try:
            item = await KnowledgeItem.get(item_id)
            if not item:
                return False
            
            # 删除关联的 KnowledgeItemInfo
            infos = await KnowledgeItemInfo.find(
                KnowledgeItemInfo.master_id == item.uid,
                KnowledgeItemInfo.tenant_id == item.tenant_id
            ).to_list()
            
            for info in infos:
                await info.delete()
            
            # 删除关联的 KnowledgeItemChunk
            chunks = await KnowledgeItemChunk.find(
                KnowledgeItemChunk.master_id == item.uid,
                KnowledgeItemChunk.tenant_id == item.tenant_id
            ).to_list()
            
            for chunk in chunks:
                await chunk.delete()
            
            # 删除主条目
            await item.delete()
            return True
        except Exception as e:
            raise DatabaseException(f"Failed to delete knowledge item with related data {item_id}: {str(e)}")


class KnowledgeItemInfoRepository:
    
    @staticmethod
    async def get_by_master_and_page(
        master_id: str, 
        page_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemInfo]:
        """根据主ID和页码获取知识条目信息"""
        try:
            info = await KnowledgeItemInfo.find_one(
                KnowledgeItemInfo.master_id == master_id,
                KnowledgeItemInfo.page_idx == page_idx,
                KnowledgeItemInfo.tenant_id == tenant_id
            )
            return info
        except Exception as e:
            raise DatabaseException(f"Failed to get knowledge item info by master and page: {str(e)}")
    
    @staticmethod
    async def create(info: KnowledgeItemInfo) -> KnowledgeItemInfo:
        """创建知识条目信息"""
        try:
            # 检查是否已存在
            existing = await KnowledgeItemInfo.find_one(
                KnowledgeItemInfo.master_id == info.master_id,
                KnowledgeItemInfo.page_idx == info.page_idx,
                KnowledgeItemInfo.tenant_id == info.tenant_id
            )
            if existing:
                raise DuplicateException("KnowledgeItemInfo", f"{info.master_id}-{info.page_idx}")
            
            created_info = await info.create()
            return created_info
        except DuplicateException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to create knowledge item info: {str(e)}")
    
    @staticmethod
    async def create_batch(infos: List[KnowledgeItemInfo]) -> List[KnowledgeItemInfo]:
        """批量创建知识条目信息"""
        try:
            if not infos:
                return []
            
            created_infos = await KnowledgeItemInfo.insert_many(infos)
            return created_infos
        except Exception as e:
            raise DatabaseException(f"Failed to create batch knowledge item infos: {str(e)}")
    
    @staticmethod
    async def find_by_master(
        master_id: str, 
        tenant_id: str,
        skip: int = 0,
        limit: int = 1000
    ) -> List[KnowledgeItemInfo]:
        """根据主ID查询知识条目信息"""
        try:
            infos = await KnowledgeItemInfo.find(
                KnowledgeItemInfo.master_id == master_id,
                KnowledgeItemInfo.tenant_id == tenant_id
            ).skip(skip).limit(limit).to_list()
            return infos
        except Exception as e:
            raise DatabaseException(f"Failed to find knowledge item infos by master: {str(e)}")
    
    @staticmethod
    async def delete_by_master(master_id: str, tenant_id: str) -> int:
        """根据主ID删除知识条目信息"""
        try:
            result = await KnowledgeItemInfo.find(
                KnowledgeItemInfo.master_id == master_id,
                KnowledgeItemInfo.tenant_id == tenant_id
            ).delete()
            return result.deleted_count
        except Exception as e:
            raise DatabaseException(f"Failed to delete knowledge item infos by master: {str(e)}")


class KnowledgeItemChunkRepository:
    
    @staticmethod
    async def get_by_master_and_idx(
        master_id: str, 
        chunk_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemChunk]:
        """根据主ID和索引获取知识条目块"""
        try:
            chunk = await KnowledgeItemChunk.find_one(
                KnowledgeItemChunk.master_id == master_id,
                KnowledgeItemChunk.chunk_idx == chunk_idx,
                KnowledgeItemChunk.tenant_id == tenant_id
            )
            return chunk
        except Exception as e:
            raise DatabaseException(f"Failed to get knowledge item chunk by master and index: {str(e)}")
    
    @staticmethod
    async def create(chunk: KnowledgeItemChunk) -> KnowledgeItemChunk:
        """创建知识条目块"""
        try:
            # 检查是否已存在
            existing = await KnowledgeItemChunk.find_one(
                KnowledgeItemChunk.master_id == chunk.master_id,
                KnowledgeItemChunk.chunk_idx == chunk.chunk_idx,
                KnowledgeItemChunk.tenant_id == chunk.tenant_id
            )
            if existing:
                raise DuplicateException("KnowledgeItemChunk", f"{chunk.master_id}-{chunk.chunk_idx}")
            
            created_chunk = await chunk.create()
            return created_chunk
        except DuplicateException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to create knowledge item chunk: {str(e)}")
    
    @staticmethod
    async def create_batch(chunks: List[KnowledgeItemChunk]) -> List[KnowledgeItemChunk]:
        """批量创建知识条目块"""
        try:
            if not chunks:
                return []
            
            created_chunks = await KnowledgeItemChunk.insert_many(chunks)
            return created_chunks
        except Exception as e:
            raise DatabaseException(f"Failed to create batch knowledge item chunks: {str(e)}")
    
    @staticmethod
    async def find_by_master(
        master_id: str, 
        tenant_id: str,
        chunk_type: Optional[ItemChunkTypeEnum] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemChunk]:
        """根据主ID查询知识条目块"""
        try:
            query = [
                KnowledgeItemChunk.master_id == master_id,
                KnowledgeItemChunk.tenant_id == tenant_id
            ]
            
            if chunk_type:
                query.append(KnowledgeItemChunk.chunk_type == chunk_type)
                
            chunks = await KnowledgeItemChunk.find(And(*query)).skip(skip).limit(limit).to_list()
            return chunks
        except Exception as e:
            raise DatabaseException(f"Failed to find knowledge item chunks by master: {str(e)}")
    
    @staticmethod
    async def find_by_master_with_types(
        master_id: str, 
        tenant_id: str,
        chunk_types: Optional[List[ItemChunkTypeEnum]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemChunk]:
        """根据主ID和类型查询知识条目块"""
        try:
            query = [
                KnowledgeItemChunk.master_id == master_id,
                KnowledgeItemChunk.tenant_id == tenant_id
            ]
            
            if chunk_types:
                query.append(In(KnowledgeItemChunk.chunk_type, chunk_types))
                
            chunks = await KnowledgeItemChunk.find(And(*query)).skip(skip).limit(limit).to_list()
            return chunks
        except Exception as e:
            raise DatabaseException(f"Failed to find knowledge item chunks by master with types: {str(e)}")
    
    @staticmethod
    async def delete_by_master(master_id: str, tenant_id: str) -> int:
        """根据主ID删除知识条目块"""
        try:
            result = await KnowledgeItemChunk.find(
                KnowledgeItemChunk.master_id == master_id,
                KnowledgeItemChunk.tenant_id == tenant_id
            ).delete()
            return result.deleted_count
        except Exception as e:
            raise DatabaseException(f"Failed to delete knowledge item chunks by master: {str(e)}")


# 仓库实例
knowledge_item_repository = KnowledgeItemRepository()    
knowledge_item_info_repository = KnowledgeItemInfoRepository()
knowledge_item_chunk_repository = KnowledgeItemChunkRepository()