# foxmask/knowledge/services/knowledge_item_service.py
from typing import List, Optional, Dict, Any, Tuple
from beanie import PydanticObjectId
from loguru import logger

from foxmask.knowledge.repositories import (
    knowledge_base_repository,
    
from foxmask.knowledge.models.knowledge_item import KnowledgeItem, KnowledgeItemInfo, KnowledgeItemChunk
from foxmask.knowledge.dtos.knowledge_item_dto import (
    KnowledgeItemCreateDTO, KnowledgeItemUpdateDTO, KnowledgeItemQueryDTO, KnowledgeItemDTO,
    KnowledgeItemInfoCreateDTO, KnowledgeItemInfoDTO, KnowledgeItemInfoUpdateDTO,
    KnowledgeItemChunkCreateDTO, KnowledgeItemChunkDTO, KnowledgeItemChunkUpdateDTO,
    KnowledgeItemWithInfosCreateDTO, KnowledgeItemChunkingDTO, 
    KnowledgeItemWithDetailsQueryDTO, BatchOperationResultDTO
)
from foxmask.core.model import Status, Visibility
from foxmask.core.exceptions import (
    ValidationException, NotFoundException, DuplicateException, ServiceException
)
from foxmask.utils.decorators import handle_exceptions, log_execution_time, validate_arguments


class KnowledgeItemService:
    
    @staticmethod
    def _entity_to_dto(entity: KnowledgeItem) -> KnowledgeItemDTO:
        """实体转DTO"""
        logger.trace(f"Converting KnowledgeItem entity to DTO: {entity.id}")
        return KnowledgeItemDTO(
            id=entity.id,
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            item_type=entity.item_type,
            source_id=entity.source_id,
            title=entity.title,
            desc=entity.desc,
            category=entity.category,
            tags=entity.tags,
            note=entity.note,
            status=entity.status,
            visibility=entity.visibility,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
            created_by=entity.created_by,
            allowed_users=entity.allowed_users,
            allowed_roles=entity.allowed_roles,
            proc_meta=entity.proc_meta,
            error_info=entity.error_info,
            metadata=entity.metadata
        )
    
    @staticmethod
    def _dto_to_entity(dto: KnowledgeItemCreateDTO) -> KnowledgeItem:
        """DTO转实体"""
        logger.trace(f"Converting KnowledgeItem DTO to entity: {dto.uid}")
        return KnowledgeItem(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            item_type=dto.item_type,
            source_id=dto.source_id,
            title=dto.title,
            desc=dto.desc,
            category=dto.category,
            tags=dto.tags,
            note=dto.note,
            status=dto.status,
            visibility=dto.visibility,
            created_by=dto.created_by,
            allowed_users=dto.allowed_users,
            allowed_roles=dto.allowed_roles,
            proc_meta=dto.proc_meta,
            metadata=dto.metadata
        )
    
    @handle_exceptions({
        Exception: "Failed to create knowledge item"
    })
    @log_execution_time
    @validate_arguments(["uid", "tenant_id", "item_type", "title"])
    async def create_item(self, create_dto: KnowledgeItemCreateDTO) -> KnowledgeItemDTO:
        logger.info(f"Creating knowledge item: {create_dto.uid} for tenant: {create_dto.tenant_id}")
        
        # 检查UID是否已存在
        existing = await KnowledgeItemRepository.get_by_uid(create_dto.uid, create_dto.tenant_id)
        if existing:
            logger.error(f"Knowledge item UID already exists: {create_dto.uid}")
            raise DuplicateException("KnowledgeItem", create_dto.uid)
        
        entity = self._dto_to_entity(create_dto)
        created_entity = await KnowledgeItemRepository.create(entity)
        
        logger.info(f"Successfully created knowledge item: {created_entity.id}")
        return self._entity_to_dto(created_entity)
    
    @handle_exceptions({
        Exception: "Failed to get knowledge item"
    })
    @log_execution_time
    async def get_item(self, item_id: PydanticObjectId) -> Optional[KnowledgeItemDTO]:
        logger.debug(f"Getting knowledge item by ID: {item_id}")
        
        entity = await KnowledgeItemRepository.get_by_id(item_id)
        if not entity:
            logger.warning(f"Knowledge item not found: {item_id}")
            return None
        
        logger.debug(f"Successfully retrieved knowledge item: {item_id}")
        return self._entity_to_dto(entity)
    
    @handle_exceptions({
        Exception: "Failed to get knowledge item by UID"
    })
    @log_execution_time
    @validate_arguments(["uid", "tenant_id"])
    async def get_item_by_uid(self, uid: str, tenant_id: str) -> Optional[KnowledgeItemDTO]:
        logger.debug(f"Getting knowledge item by UID: {uid}, tenant: {tenant_id}")
        
        entity = await KnowledgeItemRepository.get_by_uid(uid, tenant_id)
        if not entity:
            logger.warning(f"Knowledge item not found by UID: {uid}")
            return None
        
        logger.debug(f"Successfully retrieved knowledge item by UID: {uid}")
        return self._entity_to_dto(entity)
    
    @handle_exceptions({
        Exception: "Failed to update knowledge item"
    })
    @log_execution_time
    async def update_item(
        self, 
        item_id: PydanticObjectId, 
        update_dto: KnowledgeItemUpdateDTO
    ) -> Optional[KnowledgeItemDTO]:
        logger.info(f"Updating knowledge item: {item_id}")
        
        # 过滤掉None值
        update_data = {k: v for k, v in update_dto.dict().items() if v is not None}
        
        if not update_data:
            logger.warning(f"No valid update data provided for knowledge item: {item_id}")
            return await self.get_item(item_id)
        
        entity = await KnowledgeItemRepository.update(item_id, update_data)
        if not entity:
            logger.warning(f"Knowledge item not found for update: {item_id}")
            return None
        
        logger.info(f"Successfully updated knowledge item: {item_id}")
        return self._entity_to_dto(entity)
    
    @handle_exceptions({
        Exception: "Failed to delete knowledge item"
    })
    @log_execution_time
    async def delete_item(self, item_id: PydanticObjectId) -> bool:
        logger.info(f"Deleting knowledge item: {item_id}")
        
        success = await KnowledgeItemRepository.delete(item_id)
        if success:
            logger.info(f"Successfully deleted knowledge item: {item_id}")
        else:
            logger.warning(f"Knowledge item not found for deletion: {item_id}")
        
        return success
    
    @handle_exceptions({
        Exception: "Failed to query knowledge items"
    })
    @log_execution_time
    @validate_arguments(["tenant_id"])
    async def query_items(
        self, 
        query_dto: KnowledgeItemQueryDTO,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemDTO]:
        logger.info(
            f"Querying knowledge items - tenant: {query_dto.tenant_id}, "
            f"type: {query_dto.item_type}, status: {query_dto.status}, "
            f"skip: {skip}, limit: {limit}"
        )
        
        entities = await KnowledgeItemRepository.find(
            tenant_id=query_dto.tenant_id,
            item_type=query_dto.item_type,
            status=query_dto.status,
            visibility=query_dto.visibility,
            tags=query_dto.tags,
            created_by=query_dto.created_by,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"Query returned {len(entities)} knowledge items")
        return [self._entity_to_dto(entity) for entity in entities]
    
    @handle_exceptions({
        Exception: "Failed to count knowledge items"
    })
    @log_execution_time
    @validate_arguments(["tenant_id"])
    async def count_items(self, query_dto: KnowledgeItemQueryDTO) -> int:
        logger.debug(f"Counting knowledge items for tenant: {query_dto.tenant_id}")
        
        count = await KnowledgeItemRepository.count(
            tenant_id=query_dto.tenant_id,
            item_type=query_dto.item_type,
            status=query_dto.status
        )
        
        logger.debug(f"Counted {count} knowledge items")
        return count
    
    @handle_exceptions({
        Exception: "Failed to create knowledge item with infos"
    })
    @log_execution_time
    @validate_arguments(["item"])
    async def create_item_with_infos(
        self, 
        create_dto: KnowledgeItemWithInfosCreateDTO
    ) -> Tuple[KnowledgeItemDTO, List[KnowledgeItemInfoDTO]]:
        logger.info(f"Creating knowledge item with {len(create_dto.infos)} infos")
        
        # 1. 创建知识条目
        item_dto = await self.create_item(create_dto.item)
        
        # 2. 创建关联信息
        info_service = KnowledgeItemInfoService()
        created_infos = []
        
        for info_create_dto in create_dto.infos:
            # 设置主文档ID
            info_create_dto.master_id = item_dto.uid
            info_dto = await info_service.create_info(info_create_dto)
            created_infos.append(info_dto)
        
        logger.info(f"Successfully created knowledge item with {len(created_infos)} infos")
        return item_dto, created_infos
    
    @handle_exceptions({
        Exception: "Failed to chunk knowledge item"
    })
    @log_execution_time
    @validate_arguments(["item_id", "chunks"])
    async def chunk_item(
        self, 
        chunking_dto: KnowledgeItemChunkingDTO
    ) -> Tuple[Optional[KnowledgeItemDTO], List[KnowledgeItemChunkDTO]]:
        logger.info(f"Chunking knowledge item: {chunking_dto.item_id} with {len(chunking_dto.chunks)} chunks")
        
        # 1. 获取知识条目
        item = await KnowledgeItemRepository.get_by_id(chunking_dto.item_id)
        if not item:
            logger.error(f"Knowledge item not found for chunking: {chunking_dto.item_id}")
            raise NotFoundException("KnowledgeItem", str(chunking_dto.item_id))
        
        # 2. 更新知识条目元数据（如果有）
        if chunking_dto.update_metadata:
            logger.debug(f"Updating item metadata: {chunking_dto.update_metadata}")
            await item.set({"proc_meta": {**item.proc_meta, **chunking_dto.update_metadata}})
            await item.save()
        
        # 3. 创建内容块
        chunk_service = KnowledgeItemChunkService()
        created_chunks = []
        
        for chunk_create_dto in chunking_dto.chunks:
            # 设置主文档ID和租户ID
            chunk_create_dto.master_id = item.uid
            chunk_create_dto.tenant_id = item.tenant_id
            chunk_dto = await chunk_service.create_chunk(chunk_create_dto)
            created_chunks.append(chunk_dto)
        
        # 4. 返回更新后的条目和创建的块
        updated_item_dto = self._entity_to_dto(item)
        logger.info(f"Successfully chunked knowledge item with {len(created_chunks)} chunks")
        return updated_item_dto, created_chunks
    
    @handle_exceptions({
        Exception: "Failed to delete knowledge item with related data"
    })
    @log_execution_time
    async def delete_item_with_related_data(
        self, 
        item_id: PydanticObjectId
    ) -> bool:
        logger.info(f"Deleting knowledge item with related data: {item_id}")
        
        success = await KnowledgeItemRepository.delete_with_related_data(item_id)
        if success:
            logger.info(f"Successfully deleted knowledge item with related data: {item_id}")
        else:
            logger.warning(f"Knowledge item not found for deletion with related data: {item_id}")
        
        return success
    
    @handle_exceptions({
        Exception: "Failed to get knowledge item with details"
    })
    @log_execution_time
    @validate_arguments(["tenant_id"])
    async def get_item_with_details(
        self, 
        query_dto: KnowledgeItemWithDetailsQueryDTO
    ) -> Dict[str, Any]:
        logger.info(f"Getting knowledge item with details - tenant: {query_dto.tenant_id}")
        
        result = {}
        
        # 1. 获取知识条目
        if query_dto.item_id:
            item_dto = await self.get_item(query_dto.item_id)
        elif query_dto.uid:
            item_dto = await self.get_item_by_uid(query_dto.uid, query_dto.tenant_id)
        else:
            logger.error("Either item_id or uid must be provided")
            raise ValidationException("Either item_id or uid must be provided")
        
        if not item_dto:
            logger.warning("Knowledge item not found for details query")
            return result
        
        result["item"] = item_dto
        
        # 2. 获取关联信息（如果需要）
        if query_dto.include_infos:
            info_service = KnowledgeItemInfoService()
            if query_dto.info_page_idx is not None:
                # 获取指定页码的信息
                info_dto = await info_service.get_info_by_page(
                    item_dto.uid, query_dto.info_page_idx, query_dto.tenant_id
                )
                result["infos"] = [info_dto] if info_dto else []
                logger.debug(f"Retrieved {len(result['infos'])} info for specific page")
            else:
                # 获取所有信息
                infos = await KnowledgeItemInfoRepository.find_by_master(
                    item_dto.uid, query_dto.tenant_id
                )
                result["infos"] = [KnowledgeItemInfoService._entity_to_dto(info) for info in infos]
                logger.debug(f"Retrieved {len(result['infos'])} infos")
        
        # 3. 获取关联块（如果需要）
        if query_dto.include_chunks:
            chunk_service = KnowledgeItemChunkService()
            chunks = await KnowledgeItemChunkRepository.find_by_master_with_types(
                item_dto.uid, query_dto.tenant_id, query_dto.chunk_types
            )
            result["chunks"] = [KnowledgeItemChunkService._entity_to_dto(chunk) for chunk in chunks]
            logger.debug(f"Retrieved {len(result['chunks'])} chunks")
        
        logger.info(f"Successfully retrieved knowledge item with {len(result.get('infos', []))} infos and {len(result.get('chunks', []))} chunks")
        return result
    
    @handle_exceptions({
        Exception: "Failed to batch delete knowledge items"
    })
    @log_execution_time
    async def batch_delete_items(
        self, 
        item_ids: List[PydanticObjectId]
    ) -> BatchOperationResultDTO:
        logger.info(f"Batch deleting {len(item_ids)} knowledge items")
        
        total_count = len(item_ids)
        success_count = 0
        failed_count = 0
        failed_items = []
        
        for item_id in item_ids:
            try:
                success = await self.delete_item_with_related_data(item_id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_items.append(str(item_id))
            except Exception as e:
                failed_count += 1
                failed_items.append(str(item_id))
                logger.error(f"Failed to delete knowledge item {item_id}: {str(e)}")
        
        result = BatchOperationResultDTO(
            success=failed_count == 0,
            message=f"批量删除完成，成功{success_count}个，失败{failed_count}个",
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items
        )
        
        logger.info(f"Batch delete completed: {success_count} successful, {failed_count} failed")
        return result


class KnowledgeItemInfoService:
    
    @staticmethod
    def _entity_to_dto(entity: KnowledgeItemInfo) -> KnowledgeItemInfoDTO:
        """实体转DTO"""
        logger.trace(f"Converting KnowledgeItemInfo entity to DTO: {entity.id}")
        return KnowledgeItemInfoDTO(
            id=entity.id,
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            master_id=entity.master_id,
            page_idx=entity.page_idx,
            page_size=entity.page_size,
            preproc_blocks=entity.preproc_blocks,
            para_blocks=entity.para_blocks,
            discarded_blocks=entity.discarded_blocks,
            note=entity.note,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def _dto_to_entity(dto: KnowledgeItemInfoCreateDTO) -> KnowledgeItemInfo:
        """DTO转实体"""
        logger.trace(f"Converting KnowledgeItemInfo DTO to entity: {dto.uid}")
        return KnowledgeItemInfo(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            page_idx=dto.page_idx,
            page_size=dto.page_size,
            preproc_blocks=dto.preproc_blocks,
            para_blocks=dto.para_blocks,
            discarded_blocks=dto.discarded_blocks,
            note=dto.note
        )
    
    @handle_exceptions({
        Exception: "Failed to create knowledge item info"
    })
    @log_execution_time
    @validate_arguments(["uid", "tenant_id", "master_id", "page_idx"])
    async def create_info(self, create_dto: KnowledgeItemInfoCreateDTO) -> KnowledgeItemInfoDTO:
        logger.info(f"Creating knowledge item info for master: {create_dto.master_id}, page: {create_dto.page_idx}")
        
        entity = self._dto_to_entity(create_dto)
        created_entity = await KnowledgeItemInfoRepository.create(entity)
        
        logger.info(f"Successfully created knowledge item info: {created_entity.id}")
        return self._entity_to_dto(created_entity)
    
    @handle_exceptions({
        Exception: "Failed to get knowledge item info by page"
    })
    @log_execution_time
    @validate_arguments(["master_id", "page_idx", "tenant_id"])
    async def get_info_by_page(
        self, 
        master_id: str, 
        page_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemInfoDTO]:
        logger.debug(f"Getting knowledge item info - master: {master_id}, page: {page_idx}, tenant: {tenant_id}")
        
        entity = await KnowledgeItemInfoRepository.get_by_master_and_page(
            master_id, page_idx, tenant_id
        )
        if not entity:
            logger.warning(f"Knowledge item info not found for master: {master_id}, page: {page_idx}")
            return None
        
        logger.debug(f"Successfully retrieved knowledge item info: {entity.id}")
        return self._entity_to_dto(entity)
    
    @handle_exceptions({
        Exception: "Failed to create batch knowledge item infos"
    })
    @log_execution_time
    async def create_batch_infos(self, create_dtos: List[KnowledgeItemInfoCreateDTO]) -> List[KnowledgeItemInfoDTO]:
        logger.info(f"Creating batch knowledge item infos, count: {len(create_dtos)}")
        
        entities = [self._dto_to_entity(dto) for dto in create_dtos]
        created_entities = await KnowledgeItemInfoRepository.create_batch(entities)
        
        logger.info(f"Successfully created {len(created_entities)} knowledge item infos in batch")
        return [self._entity_to_dto(entity) for entity in created_entities]
    
    @handle_exceptions({
        Exception: "Failed to delete knowledge item infos by master"
    })
    @log_execution_time
    @validate_arguments(["master_id", "tenant_id"])
    async def delete_by_master(self, master_id: str, tenant_id: str) -> int:
        logger.info(f"Deleting knowledge item infos by master: {master_id}, tenant: {tenant_id}")
        
        deleted_count = await KnowledgeItemInfoRepository.delete_by_master(master_id, tenant_id)
        logger.info(f"Successfully deleted {deleted_count} knowledge item infos")
        return deleted_count


class KnowledgeItemChunkService:
    
    @staticmethod
    def _entity_to_dto(entity: KnowledgeItemChunk) -> KnowledgeItemChunkDTO:
        """实体转DTO"""
        logger.trace(f"Converting KnowledgeItemChunk entity to DTO: {entity.id}")
        return KnowledgeItemChunkDTO(
            id=entity.id,
            uid=entity.uid,
            tenant_id=entity.tenant_id,
            master_id=entity.master_id,
            chunk_idx=entity.chunk_idx,
            chunk_type=entity.chunk_type,
            text=entity.text,
            image_url=entity.image_url,
            image_data=entity.image_data,
            equation=entity.equation,
            table_data=entity.table_data,
            code_content=entity.code_content,
            code_language=entity.code_language,
            chunk_metadata=entity.chunk_metadata,
            position=entity.position,
            size=entity.size,
            vector_id=entity.vector_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    @staticmethod
    def _dto_to_entity(dto: KnowledgeItemChunkCreateDTO) -> KnowledgeItemChunk:
        """DTO转实体"""
        logger.trace(f"Converting KnowledgeItemChunk DTO to entity: {dto.uid}")
        return KnowledgeItemChunk(
            uid=dto.uid,
            tenant_id=dto.tenant_id,
            master_id=dto.master_id,
            idx=dto.idx,
            chunk_type=dto.chunk_type,
            text=dto.text,
            image_url=dto.image_url,
            image_data=dto.image_data,
            equation=dto.equation,
            table_data=dto.table_data,
            code_content=dto.code_content,
            code_language=dto.code_language,
            chunk_metadata=dto.chunk_metadata,
            position=dto.position,
            size=dto.size,
            vector_id=dto.vector_id
        )
    
    @handle_exceptions({
        Exception: "Failed to create knowledge item chunk"
    })
    @log_execution_time
    @validate_arguments(["uid", "tenant_id", "master_id", "idx", "chunk_type"])
    async def create_chunk(self, create_dto: KnowledgeItemChunkCreateDTO) -> KnowledgeItemChunkDTO:
        logger.info(f"Creating knowledge item chunk for master: {create_dto.master_id}, idx: {create_dto.idx}")
        
        entity = self._dto_to_entity(create_dto)
        created_entity = await KnowledgeItemChunkRepository.create(entity)
        
        logger.info(f"Successfully created knowledge item chunk: {created_entity.id}")
        return self._entity_to_dto(created_entity)
    
    @handle_exceptions({
        Exception: "Failed to get knowledge item chunk by index"
    })
    @log_execution_time
    @validate_arguments(["master_id", "idx", "tenant_id"])
    async def get_chunk_by_idx(
        self, 
        master_id: str, 
        idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemChunkDTO]:
        logger.debug(f"Getting knowledge item chunk - master: {master_id}, idx: {idx}, tenant: {tenant_id}")
        
        entity = await KnowledgeItemChunkRepository.get_by_master_and_idx(
            master_id, idx, tenant_id
        )
        if not entity:
            logger.warning(f"Knowledge item chunk not found for master: {master_id}, idx: {idx}")
            return None
        
        logger.debug(f"Successfully retrieved knowledge item chunk: {entity.id}")
        return self._entity_to_dto(entity)
    
    @handle_exceptions({
        Exception: "Failed to create batch knowledge item chunks"
    })
    @log_execution_time
    async def create_batch_chunks(self, create_dtos: List[KnowledgeItemChunkCreateDTO]) -> List[KnowledgeItemChunkDTO]:
        logger.info(f"Creating batch knowledge item chunks, count: {len(create_dtos)}")
        
        entities = [self._dto_to_entity(dto) for dto in create_dtos]
        created_entities = await KnowledgeItemChunkRepository.create_batch(entities)
        
        logger.info(f"Successfully created {len(created_entities)} knowledge item chunks in batch")
        return [self._entity_to_entity(entity) for entity in created_entities]
    
    @handle_exceptions({
        Exception: "Failed to delete knowledge item chunks by master"
    })
    @log_execution_time
    @validate_arguments(["master_id", "tenant_id"])
    async def delete_by_master(self, master_id: str, tenant_id: str) -> int:
        logger.info(f"Deleting knowledge item chunks by master: {master_id}, tenant: {tenant_id}")
        
        deleted_count = await KnowledgeItemChunkRepository.delete_by_master(master_id, tenant_id)
        logger.info(f"Successfully deleted {deleted_count} knowledge item chunks")
        return deleted_count