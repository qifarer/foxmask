# foxmask/knowledge/repositories/knowledge_item_repository.py
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from beanie.operators import In, Eq, And
from loguru import logger

from foxmask.knowledge.models.knowledge_item import KnowledgeItem, KnowledgeItemInfo, KnowledgeItemChunk
from foxmask.core.model import Status, Visibility
from foxmask.core.exceptions import (
    DatabaseException, NotFoundException, DuplicateException
)
from foxmask.utils.decorators import handle_exceptions, log_execution_time


class KnowledgeItemRepository:
    
    @staticmethod
    @handle_exceptions({
        ValueError: "Invalid ID format",
        Exception: "Failed to get knowledge item by ID"
    })
    @log_execution_time
    async def get_by_id(id: PydanticObjectId) -> Optional[KnowledgeItem]:
        logger.debug(f"Getting knowledge item by ID: {id}")
        item = await KnowledgeItem.get(id)
        if item:
            logger.info(f"Successfully retrieved knowledge item: {id}")
        else:
            logger.warning(f"Knowledge item not found: {id}")
        return item
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to get knowledge item by UID"
    })
    @log_execution_time
    async def get_by_uid(uid: str, tenant_id: str) -> Optional[KnowledgeItem]:
        logger.debug(f"Getting knowledge item by UID: {uid}, tenant: {tenant_id}")
        item = await KnowledgeItem.find_one(
            KnowledgeItem.uid == uid, 
            KnowledgeItem.tenant_id == tenant_id
        )
        if item:
            logger.info(f"Successfully retrieved knowledge item by UID: {uid}")
        else:
            logger.debug(f"Knowledge item not found by UID: {uid}")
        return item
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to create knowledge item"
    })
    @log_execution_time
    async def create(item: KnowledgeItem) -> KnowledgeItem:
        logger.debug(f"Creating knowledge item: {item.uid}")
        
        # 检查是否已存在
        existing = await KnowledgeItem.find_one(
            KnowledgeItem.uid == item.uid,
            KnowledgeItem.tenant_id == item.tenant_id
        )
        if existing:
            logger.error(f"Duplicate knowledge item UID: {item.uid}")
            raise DuplicateException("KnowledgeItem", item.uid)
        
        created_item = await item.create()
        logger.info(f"Successfully created knowledge item: {created_item.id}")
        return created_item
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to update knowledge item"
    })
    @log_execution_time
    async def update(id: PydanticObjectId, update_data: Dict[str, Any]) -> Optional[KnowledgeItem]:
        logger.debug(f"Updating knowledge item: {id} with data: {update_data}")
        
        item = await KnowledgeItem.get(id)
        if not item:
            logger.warning(f"Knowledge item not found for update: {id}")
            return None
        
        await item.set(update_data)
        logger.info(f"Successfully updated knowledge item: {id}")
        return item
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to delete knowledge item"
    })
    @log_execution_time
    async def delete(id: PydanticObjectId) -> bool:
        logger.debug(f"Deleting knowledge item: {id}")
        
        item = await KnowledgeItem.get(id)
        if not item:
            logger.warning(f"Knowledge item not found for deletion: {id}")
            return False
        
        await item.delete()
        logger.info(f"Successfully deleted knowledge item: {id}")
        return True
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to find knowledge items"
    })
    @log_execution_time
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
        logger.debug(
            f"Finding knowledge items - tenant: {tenant_id}, type: {item_type}, "
            f"status: {status}, skip: {skip}, limit: {limit}"
        )
        
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
        logger.info(f"Found {len(items)} knowledge items for tenant: {tenant_id}")
        return items
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to count knowledge items"
    })
    @log_execution_time
    async def count(
        tenant_id: str,
        item_type: Optional[KnowledgeItemTypeEnum] = None,
        status: Optional[Status] = None
    ) -> int:
        logger.debug(f"Counting knowledge items - tenant: {tenant_id}, type: {item_type}, status: {status}")
        
        query = [KnowledgeItem.tenant_id == tenant_id]
        
        if item_type:
            query.append(KnowledgeItem.item_type == item_type)
        if status:
            query.append(KnowledgeItem.status == status)
            
        count = await KnowledgeItem.find(And(*query)).count()
        logger.debug(f"Counted {count} knowledge items")
        return count

    @staticmethod
    @handle_exceptions({
        Exception: "Failed to delete knowledge item with related data"
    })
    @log_execution_time
    async def delete_with_related_data(item_id: PydanticObjectId) -> bool:
        logger.debug(f"Deleting knowledge item with related data: {item_id}")
        
        item = await KnowledgeItem.get(item_id)
        if not item:
            logger.warning(f"Knowledge item not found for deletion with related data: {item_id}")
            return False
        
        # 删除关联的 KnowledgeItemInfo
        infos = await KnowledgeItemInfo.find(
            KnowledgeItemInfo.master_id == item.uid,
            KnowledgeItemInfo.tenant_id == item.tenant_id
        ).to_list()
        
        logger.debug(f"Deleting {len(infos)} related info records")
        for info in infos:
            await info.delete()
        
        # 删除关联的 KnowledgeItemChunk
        chunks = await KnowledgeItemChunk.find(
            KnowledgeItemChunk.master_id == item.uid,
            KnowledgeItemChunk.tenant_id == item.tenant_id
        ).to_list()
        
        logger.debug(f"Deleting {len(chunks)} related chunk records")
        for chunk in chunks:
            await chunk.delete()
        
        # 删除主条目
        await item.delete()
        logger.info(f"Successfully deleted knowledge item and {len(infos)} infos, {len(chunks)} chunks: {item_id}")
        return True


class KnowledgeItemInfoRepository:
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to get knowledge item info by master and page"
    })
    @log_execution_time
    async def get_by_master_and_page(
        master_id: str, 
        page_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemInfo]:
        logger.debug(f"Getting knowledge item info - master: {master_id}, page: {page_idx}, tenant: {tenant_id}")
        
        info = await KnowledgeItemInfo.find_one(
            KnowledgeItemInfo.master_id == master_id,
            KnowledgeItemInfo.page_idx == page_idx,
            KnowledgeItemInfo.tenant_id == tenant_id
        )
        
        if info:
            logger.debug(f"Found knowledge item info: {info.id}")
        else:
            logger.debug(f"Knowledge item info not found for master: {master_id}, page: {page_idx}")
        
        return info
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to create knowledge item info"
    })
    @log_execution_time
    async def create(info: KnowledgeItemInfo) -> KnowledgeItemInfo:
        logger.debug(f"Creating knowledge item info for master: {info.master_id}, page: {info.page_idx}")
        
        # 检查是否已存在
        existing = await KnowledgeItemInfo.find_one(
            KnowledgeItemInfo.master_id == info.master_id,
            KnowledgeItemInfo.page_idx == info.page_idx,
            KnowledgeItemInfo.tenant_id == info.tenant_id
        )
        if existing:
            logger.error(f"Duplicate knowledge item info for master: {info.master_id}, page: {info.page_idx}")
            raise DuplicateException("KnowledgeItemInfo", f"{info.master_id}-{info.page_idx}")
        
        created_info = await info.create()
        logger.info(f"Successfully created knowledge item info: {created_info.id}")
        return created_info
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to create batch knowledge item infos"
    })
    @log_execution_time
    async def create_batch(infos: List[KnowledgeItemInfo]) -> List[KnowledgeItemInfo]:
        logger.debug(f"Creating batch knowledge item infos, count: {len(infos)}")
        
        if not infos:
            logger.warning("Empty infos list provided for batch creation")
            return []
        
        created_infos = await KnowledgeItemInfo.insert_many(infos)
        logger.info(f"Successfully created {len(created_infos)} knowledge item infos in batch")
        return created_infos
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to find knowledge item infos by master"
    })
    @log_execution_time
    async def find_by_master(
        master_id: str, 
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemInfo]:
        logger.debug(f"Finding knowledge item infos by master: {master_id}, tenant: {tenant_id}")
        
        infos = await KnowledgeItemInfo.find(
            KnowledgeItemInfo.master_id == master_id,
            KnowledgeItemInfo.tenant_id == tenant_id
        ).skip(skip).limit(limit).to_list()
        
        logger.debug(f"Found {len(infos)} knowledge item infos for master: {master_id}")
        return infos
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to delete knowledge item infos by master"
    })
    @log_execution_time
    async def delete_by_master(master_id: str, tenant_id: str) -> int:
        logger.debug(f"Deleting knowledge item infos by master: {master_id}, tenant: {tenant_id}")
        
        result = await KnowledgeItemInfo.find(
            KnowledgeItemInfo.master_id == master_id,
            KnowledgeItemInfo.tenant_id == tenant_id
        ).delete()
        
        logger.info(f"Successfully deleted {result.deleted_count} knowledge item infos for master: {master_id}")
        return result.deleted_count


class KnowledgeItemChunkRepository:
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to get knowledge item chunk by master and index"
    })
    @log_execution_time
    async def get_by_master_and_idx(
        master_id: str, 
        chunk_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemChunk]:
        logger.debug(f"Getting knowledge item chunk - master: {master_id}, idx: {idx}, tenant: {tenant_id}")
        
        chunk = await KnowledgeItemChunk.find_one(
            KnowledgeItemChunk.master_id == master_id,
            KnowledgeItemChunk.chunk_idx == chunk_idx,
            KnowledgeItemChunk.tenant_id == tenant_id
        )
        
        if chunk:
            logger.debug(f"Found knowledge item chunk: {chunk.id}")
        else:
            logger.debug(f"Knowledge item chunk not found for master: {master_id}, idx: {idx}")
        
        return chunk
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to create knowledge item chunk"
    })
    @log_execution_time
    async def create(chunk: KnowledgeItemChunk) -> KnowledgeItemChunk:
        logger.debug(f"Creating knowledge item chunk for master: {chunk.master_id}, idx: {chunk.idx}")
        
        # 检查是否已存在
        existing = await KnowledgeItemChunk.find_one(
            KnowledgeItemChunk.master_id == chunk.master_id,
            KnowledgeItemChunk.idx == chunk.idx,
            KnowledgeItemChunk.tenant_id == chunk.tenant_id
        )
        if existing:
            logger.error(f"Duplicate knowledge item chunk for master: {chunk.master_id}, idx: {chunk.idx}")
            raise DuplicateException("KnowledgeItemChunk", f"{chunk.master_id}-{chunk.idx}")
        
        created_chunk = await chunk.create()
        logger.info(f"Successfully created knowledge item chunk: {created_chunk.id}")
        return created_chunk
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to create batch knowledge item chunks"
    })
    @log_execution_time
    async def create_batch(chunks: List[KnowledgeItemChunk]) -> List[KnowledgeItemChunk]:
        logger.debug(f"Creating batch knowledge item chunks, count: {len(chunks)}")
        
        if not chunks:
            logger.warning("Empty chunks list provided for batch creation")
            return []
        
        created_chunks = await KnowledgeItemChunk.insert_many(chunks)
        logger.info(f"Successfully created {len(created_chunks)} knowledge item chunks in batch")
        return created_chunks
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to find knowledge item chunks by master"
    })
    @log_execution_time
    async def find_by_master(
        master_id: str, 
        tenant_id: str,
        chunk_type: Optional[ItemChunkTypeEnum] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemChunk]:
        logger.debug(f"Finding knowledge item chunks by master: {master_id}, type: {chunk_type}")
        
        query = [
            KnowledgeItemChunk.master_id == master_id,
            KnowledgeItemChunk.tenant_id == tenant_id
        ]
        
        if chunk_type:
            query.append(KnowledgeItemChunk.chunk_type == chunk_type)
            
        chunks = await KnowledgeItemChunk.find(And(*query)).skip(skip).limit(limit).to_list()
        logger.debug(f"Found {len(chunks)} knowledge item chunks for master: {master_id}")
        return chunks
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to find knowledge item chunks by master with types"
    })
    @log_execution_time
    async def find_by_master_with_types(
        master_id: str, 
        tenant_id: str,
        chunk_types: Optional[List[ItemChunkTypeEnum]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemChunk]:
        logger.debug(f"Finding knowledge item chunks by master with types: {master_id}, types: {chunk_types}")
        
        query = [
            KnowledgeItemChunk.master_id == master_id,
            KnowledgeItemChunk.tenant_id == tenant_id
        ]
        
        if chunk_types:
            query.append(In(KnowledgeItemChunk.chunk_type, chunk_types))
            
        chunks = await KnowledgeItemChunk.find(And(*query)).skip(skip).limit(limit).to_list()
        logger.debug(f"Found {len(chunks)} knowledge item chunks for master: {master_id} with types")
        return chunks
    
    @staticmethod
    @handle_exceptions({
        Exception: "Failed to delete knowledge item chunks by master"
    })
    @log_execution_time
    async def delete_by_master(master_id: str, tenant_id: str) -> int:
        logger.debug(f"Deleting knowledge item chunks by master: {master_id}, tenant: {tenant_id}")
        
        result = await KnowledgeItemChunk.find(
            KnowledgeItemChunk.master_id == master_id,
            KnowledgeItemChunk.tenant_id == tenant_id
        ).delete()
        
        logger.info(f"Successfully deleted {result.deleted_count} knowledge item chunks for master: {master_id}")
        return result.deleted_count