# foxmask/knowledge/services/knowledge_item_service.py
from typing import List, Optional, Dict, Any, Tuple
from beanie import PydanticObjectId
from loguru import logger
import os
from uuid import uuid4
from datetime import datetime, timezone

from foxmask.core.model import Status, Visibility
from foxmask.knowledge.models import (
    KnowledgeItem, KnowledgeItemInfo, KnowledgeItemChunk,
    KnowledgeItemTypeEnum, ItemChunkTypeEnum
)    
from foxmask.knowledge.dtos import (
    KnowledgeItemCreateDTO, KnowledgeItemUpdateDTO, KnowledgeItemQueryDTO, KnowledgeItemDTO,
    KnowledgeItemInfoCreateDTO, KnowledgeItemInfoDTO, KnowledgeItemInfoUpdateDTO,
    KnowledgeItemChunkCreateDTO, KnowledgeItemChunkDTO, KnowledgeItemChunkUpdateDTO,
    KnowledgeItemWithInfosCreateDTO, KnowledgeItemChunkingDTO, 
    KnowledgeItemWithDetailsQueryDTO, BatchOperationResultDTO
)
from foxmask.knowledge.repositories import (
    knowledge_base_repository,
    knowledge_item_repository,
    knowledge_item_info_repository,
    knowledge_item_chunk_repository,
)
from foxmask.file.repositories import get_repository_manager
from foxmask.file.enums import FileTypeEnum, UploadProcStatusEnum
from foxmask.core.exceptions import (
    ValidationException, NotFoundException, DuplicateException, ServiceException
)
from foxmask.utils.minio_client import minio_client
from foxmask.utils.mineru_parser import MineruParser, BackendType, ParseMethod
from foxmask.utils.chunk_content import chunk_markdown_content

class KnowledgeItemService:
    def __init__(self):
        self.file_repository = get_repository_manager().file_repository
        pass
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
    ## create
    async def create_item(self, create_dto: KnowledgeItemCreateDTO) -> KnowledgeItemDTO:
        """创建知识条目"""
        logger.info(f"Creating knowledge item: {create_dto.uid} for tenant: {create_dto.tenant_id}")
        
        try:
            # 参数验证
            if not create_dto.uid or not create_dto.tenant_id or not create_dto.item_type or not create_dto.title:
                raise ValidationException("Missing required fields: uid, tenant_id, item_type, title")
            
            # 检查UID是否已存在
            existing = await knowledge_item_repository.get_by_uid(create_dto.uid, create_dto.tenant_id)
            if existing:
                raise DuplicateException("KnowledgeItem", create_dto.uid)
            
            entity = self._dto_to_entity(create_dto)
            created_entity = await knowledge_item_repository.create(entity)
            
            logger.info(f"Successfully created knowledge item: {created_entity.id}")
            return self._entity_to_dto(created_entity)
            
        except (ValidationException, DuplicateException):
            raise
        except Exception as e:
            logger.error(f"Failed to create knowledge item {create_dto.uid}: {str(e)}")
            raise ServiceException(f"Failed to create knowledge item: {str(e)}")
    
    async def create_item_with_infos(
        self, 
        create_dto: KnowledgeItemWithInfosCreateDTO
    ) -> Tuple[KnowledgeItemDTO, List[KnowledgeItemInfoDTO]]:
        """创建知识条目及其关联信息"""
        logger.info(f"Creating knowledge item with {len(create_dto.infos)} infos")
        
        try:
            # 参数验证
            if not create_dto.item:
                raise ValidationException("Item is required")
            
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
            
        except Exception as e:
            logger.error(f"Failed to create knowledge item with infos: {str(e)}")
            raise ServiceException(f"Failed to create knowledge item with infos: {str(e)}")
    
    async def create_item_from_file(
        self, 
        tenant_id: str, 
        file_id: str
    ) -> Tuple[KnowledgeItemDTO, List[KnowledgeItemInfoDTO]]:
        """从文件创建知识条目"""
        logger.info(f"Creating knowledge item from file: {file_id} for tenant: {tenant_id}")
        
        try:
            # 获取文件对象
            file = await self.file_repository .get_file_by_file_id(file_id)
            if not file:
                raise NotFoundException("File", file_id)
            
            if file.file_type != FileTypeEnum.PDF:
                raise ValidationException(f"文件类型不支持: {file.file_type}")
        
            if file.status != UploadProcStatusEnum.UPLOADED:
                raise ValidationException(f"文件状态异常: {file.status}")
            
            # 检查是否已存在
            existing_item = await knowledge_item_repository.get_by_source_id(source_id=file_id, tenant_id=tenant_id)
            if existing_item:
                raise DuplicateException("KnowledgeItem", f"source_id:{file_id}")
            
            bucket_name = file.minio_bucket    
            object_name = file.minio_object_name
            
            if not bucket_name or not object_name:
                raise ValidationException(f"文件存储地址错误：{file_id}")
                
            # 创建临时文件路径
            temp_dir = f"/tmp/{tenant_id}"
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = f"{temp_dir}/{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            try:
                # 从MinIO下载文件
                download_success = await minio_client.download_file(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=temp_file_path
                )
                
                if not download_success:
                    raise ServiceException("Failed to download file from MinIO")
                
                logger.info(f"Successfully downloaded file from MinIO: {bucket_name}/{object_name}")
                
                # 解析PDF文件
                parser = MineruParser(
                    output_dir=temp_dir,
                    lang="ch",
                    backend=BackendType.PIPELINE,
                    method=ParseMethod.AUTO
                )
                json_info = parser.extract_json_info(temp_file_path)
                
                if not json_info:
                    raise ServiceException("PDF解析失败: json_info为空")
                
                pdf_info = json_info.get("pdf_info")
                if not pdf_info:
                    raise ServiceException("PDF解析失败: pdf_info为空")
                
                # 使用DTO创建知识条目
                item_create_dto = KnowledgeItemCreateDTO(
                    uid=str(uuid4()),
                    tenant_id=file.tenant_id,
                    item_type=KnowledgeItemTypeEnum.FILE,
                    source_id=file_id,
                    title=file.filename,
                    desc=file.description,
                    metadata={
                        "type": file.filename,
                        "name": file.minio_object_name,
                        "path": file.minio_bucket,
                        "url": file.url,
                        "keyword": file_id,
                        "size": file.file_size,
                        "updateAt": file.created_at,      
                    },
                    tags=["FILE"],
                    note="Created from PDF file",
                    visibility=Visibility.PUBLIC,
                    status=Status.DRAFT,
                    created_by="SYSTEM",
                    allowed_users=file.allowed_users,
                    allowed_roles=file.allowed_roles
                )
   
                # 创建知识内容
                infos_create_dto: List[KnowledgeItemInfoCreateDTO] = []
                for chunk in pdf_info:
                    info_create_dto = KnowledgeItemInfoCreateDTO(
                        uid=str(uuid4()),
                        tenant_id=item_create_dto.tenant_id,
                        master_id=item_create_dto.uid,
                        page_idx=chunk.get("page_idx"),
                        page_size=chunk.get("page_size"),
                        preproc_blocks=chunk.get("preproc_blocks"),
                        para_blocks=chunk.get("para_blocks"),
                        discarded_blocks=chunk.get("discarded_blocks"),    
                    )
                    infos_create_dto.append(info_create_dto)

                item_infos_create_dto = KnowledgeItemWithInfosCreateDTO(
                    item=item_create_dto, infos=infos_create_dto
                )
                
                # 创建知识条目
                item_dto, infos_dto = await self.create_item_with_infos(item_infos_create_dto)
                
                # 更新状态为活跃
                update_dto = KnowledgeItemUpdateDTO(status=Status.ACTIVE)
                updated_item = await self.update_item(item_dto.id, update_dto)
                
                if not updated_item:
                    raise ServiceException(f"创建知识条目状态更新失败: {item_dto.uid}")
                
                # 更新文件状态为完成
                await self.file_repository.update_file_status(file_id=file_id, status=UploadProcStatusEnum.COMPLETED)
                
                logger.info(f"Successfully created knowledge item from file: {file_id}")
                return updated_item, infos_dto
                
            except Exception as e:
                logger.error(f"Error processing file {file_id}: {str(e)}")
                await self.file_repository.update_file_status(file_id=file_id, status=UploadProcStatusEnum.FAILED)
                raise ServiceException(f"文件处理失败: {str(e)}")
                
        except (NotFoundException, ValidationException, DuplicateException, ServiceException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating knowledge item from file {file_id}: {str(e)}")
            raise ServiceException(f"创建知识条目失败: {str(e)}")
        finally:
            # 清理临时文件
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up temporary file: {cleanup_error}")
    
    async def parse_item_info_to_markdown(
        self, 
        tenant_id: str, 
        item_id: str
    ) -> Optional[KnowledgeItem]:
        
        """从文件创建知识条目"""
        logger.info(f"parse_item_info_to_markdown: {item_id} for tenant: {tenant_id}")
        
        try:
            item_entity = await knowledge_item_repository.get_by_uid(item_id, tenant_id)
            # 转化为：MD
            infos_entity = await knowledge_item_info_repository.find_by_master(
                master_id=item_id, 
                tenant_id=tenant_id
            )
            pdf_infos = []
            for info in infos_entity:
                pdf_infos.append({
                    "page_idx": info.page_idx,
                    "page_size": info.page_size,
                    "preproc_blocks": info.preproc_blocks,
                    "para_blocks": info.para_blocks,
                    "discarded_blocks": info.discarded_blocks,
                })
            if not pdf_infos and len(pdf_infos)<1:
                raise Exception(f"PDF信息无效: {item_id}")
            # 解析PDF文件
            temp_dir = f"/tmp/{tenant_id}"
            parser = MineruParser(
                output_dir=temp_dir,
                lang="ch",
                backend=BackendType.PIPELINE,
                method=ParseMethod.AUTO
            )
            content_list = parser.json_to_text(pdf_info=pdf_infos,local_image_dir=temp_dir)
             
            for idx,value in enumerate(content_list):
                chunk_create_dto= KnowledgeItemChunkCreateDTO(
                        uid = str(uuid4()),
                        tenant_id=tenant_id,
                        master_id=item_id,
                        chunk_idx=idx,
                        page_idx=value.get("page_idx"),
                        chunk_type=value.get("type"),
                        text=value.get("text"),
                        image_url=value.get("img_path",""),
                        image_data=""
                    )
            
                entity = knowledge_item_chunk_service._dto_to_entity(chunk_create_dto)
                created_entity = await knowledge_item_chunk_repository.create(entity)
            
            return item_entity
        except Exception as e:
            logger.error(f"parse_item_info_to_markdown: {item_id}: {str(e)}")
            raise ServiceException(f"解析知识条目失败: {str(e)}")
        

    async def get_item(self, item_id: PydanticObjectId) -> Optional[KnowledgeItemDTO]:
        """获取知识条目"""
        logger.debug(f"Getting knowledge item by ID: {item_id}")
        
        try:
            entity = await knowledge_item_repository.get_by_id(item_id)
            if not entity:
                logger.warning(f"Knowledge item not found: {item_id}")
                return None
            
            logger.debug(f"Successfully retrieved knowledge item: {item_id}")
            return self._entity_to_dto(entity)
            
        except Exception as e:
            logger.error(f"Failed to get knowledge item {item_id}: {str(e)}")
            raise ServiceException(f"Failed to get knowledge item: {str(e)}")
    
    
    async def get_item_by_uid(self, uid: str, tenant_id: str) -> Optional[KnowledgeItemDTO]:
        """通过UID获取知识条目"""
        logger.debug(f"Getting knowledge item by UID: {uid}, tenant: {tenant_id}")
        
        try:
            # 参数验证
            if not uid or not tenant_id:
                raise ValidationException("UID and tenant_id are required")
            
            entity = await knowledge_item_repository.get_by_uid(uid, tenant_id)
            if not entity:
                logger.warning(f"Knowledge item not found by UID: {uid}")
                return None
            
            logger.debug(f"Successfully retrieved knowledge item by UID: {uid}")
            return self._entity_to_dto(entity)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge item by UID {uid}: {str(e)}")
            raise ServiceException(f"Failed to get knowledge item by UID: {str(e)}")
    
    async def update_item(
        self, 
        item_id: PydanticObjectId, 
        update_dto: KnowledgeItemUpdateDTO
    ) -> Optional[KnowledgeItemDTO]:
        """更新知识条目"""
        logger.info(f"Updating knowledge item: {item_id}")
        
        try:
            # 过滤掉None值
            update_data = {k: v for k, v in update_dto.dict().items() if v is not None}
            
            if not update_data:
                logger.warning(f"No valid update data provided for knowledge item: {item_id}")
                return await self.get_item(item_id)
            
            entity = await knowledge_item_repository.update(item_id, update_data)
            if not entity:
                logger.warning(f"Knowledge item not found for update: {item_id}")
                return None
            
            logger.info(f"Successfully updated knowledge item: {item_id}")
            return self._entity_to_dto(entity)
            
        except Exception as e:
            logger.error(f"Failed to update knowledge item {item_id}: {str(e)}")
            raise ServiceException(f"Failed to update knowledge item: {str(e)}")
    
    async def delete_item(self, item_id: PydanticObjectId) -> bool:
        """删除知识条目"""
        logger.info(f"Deleting knowledge item: {item_id}")
        
        try:
            success = await knowledge_item_repository.delete(item_id)
            if success:
                logger.info(f"Successfully deleted knowledge item: {item_id}")
            else:
                logger.warning(f"Knowledge item not found for deletion: {item_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge item {item_id}: {str(e)}")
            raise ServiceException(f"Failed to delete knowledge item: {str(e)}")
    
    async def query_items(
        self, 
        query_dto: KnowledgeItemQueryDTO,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeItemDTO]:
        """查询知识条目"""
        logger.info(
            f"Querying knowledge items - tenant: {query_dto.tenant_id}, "
            f"type: {query_dto.item_type}, status: {query_dto.status}, "
            f"skip: {skip}, limit: {limit}"
        )
        
        try:
            # 参数验证
            if not query_dto.tenant_id:
                raise ValidationException("Tenant ID is required")
            
            entities = await knowledge_item_repository.find(
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
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to query knowledge items: {str(e)}")
            raise ServiceException(f"Failed to query knowledge items: {str(e)}")
    
    async def count_items(self, query_dto: KnowledgeItemQueryDTO) -> int:
        """统计知识条目数量"""
        logger.debug(f"Counting knowledge items for tenant: {query_dto.tenant_id}")
        
        try:
            # 参数验证
            if not query_dto.tenant_id:
                raise ValidationException("Tenant ID is required")
            
            count = await knowledge_item_repository.count(
                tenant_id=query_dto.tenant_id,
                item_type=query_dto.item_type,
                status=query_dto.status
            )
            
            logger.debug(f"Counted {count} knowledge items")
            return count
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to count knowledge items: {str(e)}")
            raise ServiceException(f"Failed to count knowledge items: {str(e)}")
    
    async def chunk_item(
        self, 
        chunking_dto: KnowledgeItemChunkingDTO
    ) -> Tuple[Optional[KnowledgeItemDTO], List[KnowledgeItemChunkDTO]]:
        """分块知识条目"""
        logger.info(f"Chunking knowledge item: {chunking_dto.item_id} with {len(chunking_dto.chunks)} chunks")
        
        try:
            # 参数验证
            if not chunking_dto.item_id or not chunking_dto.chunks:
                raise ValidationException("Item ID and chunks are required")
            
            # 1. 获取知识条目
            item = await knowledge_item_repository.get_by_id(chunking_dto.item_id)
            if not item:
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
            
        except (ValidationException, NotFoundException):
            raise
        except Exception as e:
            logger.error(f"Failed to chunk knowledge item {chunking_dto.item_id}: {str(e)}")
            raise ServiceException(f"Failed to chunk knowledge item: {str(e)}")
    
    async def delete_item_with_related_data(
        self, 
        item_id: PydanticObjectId
    ) -> bool:
        """删除知识条目及相关数据"""
        logger.info(f"Deleting knowledge item with related data: {item_id}")
        
        try:
            success = await knowledge_item_repository.delete_with_related_data(item_id)
            if success:
                logger.info(f"Successfully deleted knowledge item with related data: {item_id}")
            else:
                logger.warning(f"Knowledge item not found for deletion with related data: {item_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge item with related data {item_id}: {str(e)}")
            raise ServiceException(f"Failed to delete knowledge item with related data: {str(e)}")
    
    async def get_item_with_details(
        self, 
        query_dto: KnowledgeItemWithDetailsQueryDTO
    ) -> Dict[str, Any]:
        """获取知识条目详情"""
        logger.info(f"Getting knowledge item with details - tenant: {query_dto.tenant_id}")
        
        try:
            # 参数验证
            if not query_dto.tenant_id:
                raise ValidationException("Tenant ID is required")
            
            result = {}
            
            # 1. 获取知识条目
            if query_dto.item_id:
                item_dto = await self.get_item(query_dto.item_id)
            elif query_dto.uid:
                item_dto = await self.get_item_by_uid(query_dto.uid, query_dto.tenant_id)
            else:
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
                    infos = await knowledge_item_info_repository.find_by_master(
                        item_dto.uid, query_dto.tenant_id
                    )
                    result["infos"] = [KnowledgeItemInfoService._entity_to_dto(info) for info in infos]
                    logger.debug(f"Retrieved {len(result['infos'])} infos")
            
            # 3. 获取关联块（如果需要）
            if query_dto.include_chunks:
                chunk_service = KnowledgeItemChunkService()
                chunks = await knowledge_item_chunk_repository.find_by_master_with_types(
                    item_dto.uid, query_dto.tenant_id, query_dto.chunk_types
                )
                result["chunks"] = [KnowledgeItemChunkService._entity_to_dto(chunk) for chunk in chunks]
                logger.debug(f"Retrieved {len(result['chunks'])} chunks")
            
            logger.info(f"Successfully retrieved knowledge item with {len(result.get('infos', []))} infos and {len(result.get('chunks', []))} chunks")
            return result
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge item with details: {str(e)}")
            raise ServiceException(f"Failed to get knowledge item with details: {str(e)}")
    
    async def batch_delete_items(
        self, 
        item_ids: List[PydanticObjectId]
    ) -> BatchOperationResultDTO:
        """批量删除知识条目"""
        logger.info(f"Batch deleting {len(item_ids)} knowledge items")
        
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to batch delete knowledge items: {str(e)}")
            raise ServiceException(f"Failed to batch delete knowledge items: {str(e)}")


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
    
    async def create_info(self, create_dto: KnowledgeItemInfoCreateDTO) -> KnowledgeItemInfoDTO:
        """创建知识条目信息"""
        logger.info(f"Creating knowledge item info for master: {create_dto.master_id}, page: {create_dto.page_idx}")
        
        try:
            # 参数验证
            if not create_dto.uid or not create_dto.tenant_id or not create_dto.master_id or create_dto.page_idx is None:
                raise ValidationException("Missing required fields: uid, tenant_id, master_id, page_idx")
            
            entity = self._dto_to_entity(create_dto)
            created_entity = await knowledge_item_info_repository.create(entity)
            
            logger.info(f"Successfully created knowledge item info: {created_entity.id}")
            return self._entity_to_dto(created_entity)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to create knowledge item info: {str(e)}")
            raise ServiceException(f"Failed to create knowledge item info: {str(e)}")
    
    async def get_info_by_page(
        self, 
        master_id: str, 
        page_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemInfoDTO]:
        """通过页码获取知识条目信息"""
        logger.debug(f"Getting knowledge item info - master: {master_id}, page: {page_idx}, tenant: {tenant_id}")
        
        try:
            # 参数验证
            if not master_id or page_idx is None or not tenant_id:
                raise ValidationException("Master ID, page index and tenant ID are required")
            
            entity = await knowledge_item_info_repository.get_by_master_and_page(
                master_id, page_idx, tenant_id
            )
            if not entity:
                logger.warning(f"Knowledge item info not found for master: {master_id}, page: {page_idx}")
                return None
            
            logger.debug(f"Successfully retrieved knowledge item info: {entity.id}")
            return self._entity_to_dto(entity)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge item info by page: {str(e)}")
            raise ServiceException(f"Failed to get knowledge item info by page: {str(e)}")
    
    async def create_batch_infos(self, create_dtos: List[KnowledgeItemInfoCreateDTO]) -> List[KnowledgeItemInfoDTO]:
        """批量创建知识条目信息"""
        logger.info(f"Creating batch knowledge item infos, count: {len(create_dtos)}")
        
        try:
            entities = [self._dto_to_entity(dto) for dto in create_dtos]
            created_entities = await knowledge_item_info_repository.create_batch(entities)
            
            logger.info(f"Successfully created {len(created_entities)} knowledge item infos in batch")
            return [self._entity_to_dto(entity) for entity in created_entities]
            
        except Exception as e:
            logger.error(f"Failed to create batch knowledge item infos: {str(e)}")
            raise ServiceException(f"Failed to create batch knowledge item infos: {str(e)}")
    
    async def delete_by_master(self, master_id: str, tenant_id: str) -> int:
        """通过主ID删除知识条目信息"""
        logger.info(f"Deleting knowledge item infos by master: {master_id}, tenant: {tenant_id}")
        
        try:
            # 参数验证
            if not master_id or not tenant_id:
                raise ValidationException("Master ID and tenant ID are required")
            
            deleted_count = await knowledge_item_info_repository.delete_by_master(master_id, tenant_id)
            logger.info(f"Successfully deleted {deleted_count} knowledge item infos")
            return deleted_count
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete knowledge item infos by master: {str(e)}")
            raise ServiceException(f"Failed to delete knowledge item infos by master: {str(e)}")


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
            page_idx=entity.page_idx,
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
            page_idx=dto.page_idx,
            chunk_idx=dto.chunk_idx,
            chunk_type=dto.chunk_type,
            text=dto.text,
            image_url=dto.image_url,
            image_data=dto.image_data,
       
        )
    
    async def create_chunk(self, create_dto: KnowledgeItemChunkCreateDTO) -> KnowledgeItemChunkDTO:
        """创建知识条目块"""
        logger.info(f"Creating knowledge item chunk for master: {create_dto.master_id}, chunk_idx: {create_dto.chunk_idx}")
        
        try:
            # 参数验证
            if not create_dto.uid or not create_dto.tenant_id or not create_dto.master_id or create_dto.chunk_idx is None or not create_dto.chunk_type:
                raise ValidationException("Missing required fields: uid, tenant_id, master_id, chunk_idx, chunk_type")
            
            entity = self._dto_to_entity(create_dto)
            created_entity = await knowledge_item_chunk_repository.create(entity)
            
            logger.info(f"Successfully created knowledge item chunk: {created_entity.id}")
            return self._entity_to_dto(created_entity)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to create knowledge item chunk: {str(e)}")
            raise ServiceException(f"Failed to create knowledge item chunk: {str(e)}")
    
    async def get_chunk_by_idx(
        self, 
        master_id: str, 
        chunk_idx: int, 
        tenant_id: str
    ) -> Optional[KnowledgeItemChunkDTO]:
        """通过索引获取知识条目块"""
        logger.debug(f"Getting knowledge item chunk - master: {master_id}, chunk_idx: {chunk_idx}, tenant: {tenant_id}")
        
        try:
            # 参数验证
            if not master_id or chunk_idx is None or not tenant_id:
                raise ValidationException("Master ID, index and tenant ID are required")
            
            entity = await knowledge_item_chunk_repository.get_by_master_and_idx(
                master_id, chunk_idx, tenant_id
            )
            if not entity:
                logger.warning(f"Knowledge item chunk not found for master: {master_id}, chunk_idx: {chunk_idx}")
                return None
            
            logger.debug(f"Successfully retrieved knowledge item chunk: {entity.id}")
            return self._entity_to_dto(entity)
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to get knowledge item chunk by index: {str(e)}")
            raise ServiceException(f"Failed to get knowledge item chunk by index: {str(e)}")
    
    async def create_batch_chunks(self, create_dtos: List[KnowledgeItemChunkCreateDTO]) -> List[KnowledgeItemChunkDTO]:
        """批量创建知识条目块"""
        logger.info(f"Creating batch knowledge item chunks, count: {len(create_dtos)}")
        
        try:
            entities = [self._dto_to_entity(dto) for dto in create_dtos]
            created_entities = await knowledge_item_chunk_repository.create_batch(entities)
            
            logger.info(f"Successfully created {len(created_entities)} knowledge item chunks in batch")
            return [self._entity_to_dto(entity) for entity in created_entities]
            
        except Exception as e:
            logger.error(f"Failed to create batch knowledge item chunks: {str(e)}")
            raise ServiceException(f"Failed to create batch knowledge item chunks: {str(e)}")
    
    async def delete_by_master(self, master_id: str, tenant_id: str) -> int:
        """通过主ID删除知识条目块"""
        logger.info(f"Deleting knowledge item chunks by master: {master_id}, tenant: {tenant_id}")
        
        try:
            # 参数验证
            if not master_id or not tenant_id:
                raise ValidationException("Master ID and tenant ID are required")
            
            deleted_count = await knowledge_item_chunk_repository.delete_by_master(master_id, tenant_id)
            logger.info(f"Successfully deleted {deleted_count} knowledge item chunks")
            return deleted_count
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete knowledge item chunks by master: {str(e)}")
            raise ServiceException(f"Failed to delete knowledge item chunks by master: {str(e)}")


# 服务实例
knowledge_item_service = KnowledgeItemService()
knowledge_item_info_service = KnowledgeItemInfoService()
knowledge_item_chunk_service = KnowledgeItemChunkService()