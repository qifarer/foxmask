# foxmask/knowledge/resolvers/knowledge_item_resolver.py
import strawberry
from typing import List, Optional, Union
from beanie import PydanticObjectId
from strawberry.types import Info
from loguru import logger
from functools import wraps
import asyncio

from foxmask.knowledge.services import (
    knowledge_item_service,
    knowledge_item_chunk_service,
    knowledge_item_info_service,
)
from foxmask.knowledge.dtos import (
    KnowledgeItemDTO,
    KnowledgeItemCreateDTO,
    KnowledgeItemUpdateDTO,
    KnowledgeItemQueryDTO,
    KnowledgeItemInfoDTO,
    KnowledgeItemInfoCreateDTO,
    KnowledgeItemInfoUpdateDTO,
    KnowledgeItemInfoQueryDTO,
    KnowledgeItemChunkDTO,
    KnowledgeItemChunkCreateDTO,
    KnowledgeItemChunkUpdateDTO,
    KnowledgeItemChunkQueryDTO,
    KnowledgeItemWithInfosCreateDTO,
    KnowledgeItemChunkingDTO,
    KnowledgeItemWithDetailsQueryDTO,
)
from foxmask.knowledge.graphql.schemas import (
    KnowledgeItemChunkCreateInput,
    KnowledgeItemChunkingInput,
    KnowledgeItemChunkingResult,
    KnowledgeItemChunkSchema,
    KnowledgeItemCreateInput,
    KnowledgeItemInfoCreateInput,
    KnowledgeItemInfoSchema,
    KnowledgeItemPageInfo,
    KnowledgeItemQueryInput,
    KnowledgeItemSchema,
    MutationResult,
    BatchDeleteInput,
    BatchOperationResult,
    KnowledgeItemUpdateInput,
    KnowledgeItemWithDetailsQueryInput,
    KnowledgeItemWithDetailsSchema,
    KnowledgeItemWithInfosCreateInput,
    KnowledgeItemWithInfosCreateResult,
)
from foxmask.core.exceptions import (
    KnowledgeBaseException,
    ValidationException,
    NotFoundException,
    DuplicateException,
    PermissionException,
)
from foxmask.file.enums import FileTypeEnum
from foxmask.core.enums import Status, Visibility


def handle_graphql_errors(func):
    """GraphQL错误处理装饰器，保留原始函数的类型注解"""
    @wraps(func)
    async def async_wrapper(self, info: Info, input: Optional[Union[KnowledgeItemCreateInput, KnowledgeItemUpdateInput, KnowledgeItemChunkingInput, KnowledgeItemWithInfosCreateInput, BatchDeleteInput]] = None, item_id: Optional[str] = None):
        try:
            # 根据函数签名动态调用
            if item_id is not None:
                return await func(self, item_id=item_id, input=input, info=info)
            return await func(self, input=input, info=info)
        except KnowledgeBaseException as e:
            logger.warning(f"Business error in GraphQL resolver: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GraphQL resolver: {str(e)}")
            raise KnowledgeBaseException(
                "An internal error occurred",
                "INTERNAL_ERROR",
                {"resolver": func.__name__}
            )

    @wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except KnowledgeBaseException as e:
            logger.warning(f"Business error in GraphQL resolver: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GraphQL resolver: {str(e)}")
            raise KnowledgeBaseException(
                "An internal error occurred",
                "INTERNAL_ERROR",
                {"resolver": func.__name__}
            )

    # 检查函数是否为异步函数
    if asyncio.iscoroutinefunction(func):
        async_wrapper.__annotations__ = func.__annotations__
        return async_wrapper
    return sync_wrapper


def _convert_knowledge_item_input_to_dto(input_data: KnowledgeItemCreateInput) -> KnowledgeItemCreateDTO:
    """转换KnowledgeItem输入为DTO"""
    logger.debug("Converting KnowledgeItem input to DTO")
    return KnowledgeItemCreateDTO(
        uid=input_data.uid,
        tenant_id=input_data.tenant_id,
        item_type=FileTypeEnum[input_data.item_type.name],  # Map GraphQL enum to shared enum
        source_id=input_data.source_id,
        title=input_data.title,
        desc=input_data.desc,
        category=input_data.category,
        tags=input_data.tags or [],
        note=input_data.note,
        status=StatusEnum[input_data.status.name],
        visibility=VisibilityEnum[input_data.visibility.name],
        created_by=input_data.created_by,
        allowed_users=input_data.allowed_users or [],
        allowed_roles=input_data.allowed_roles or [],
        proc_meta=input_data.proc_meta or {},
        metadata=input_data.metadata or {},
    )


def _convert_knowledge_item_info_input_to_dto(input_data: KnowledgeItemInfoCreateInput) -> KnowledgeItemInfoCreateDTO:
    """转换KnowledgeItemInfo输入为DTO"""
    logger.debug("Converting KnowledgeItemInfo input to DTO")
    return KnowledgeItemInfoCreateDTO(
        uid=input_data.uid,
        tenant_id=input_data.tenant_id,
        master_id=input_data.master_id,
        page_idx=input_data.page_idx,
        page_size=input_data.page_size or {},
        preproc_blocks=input_data.preproc_blocks or [],
        para_blocks=input_data.para_blocks or [],
        discarded_blocks=input_data.discarded_blocks or [],
        note=input_data.note,
    )


def _convert_knowledge_item_chunk_input_to_dto(input_data: KnowledgeItemChunkCreateInput) -> KnowledgeItemChunkCreateDTO:
    """转换KnowledgeItemChunk输入为DTO"""
    logger.debug("Converting KnowledgeItemChunk input to DTO")
    return KnowledgeItemChunkCreateDTO(
        uid=input_data.uid,
        tenant_id=input_data.tenant_id,
        master_id=input_data.master_id,
        chunk_idx=input_data.chunk_idx,
        chunk_type=FileTypeEnum[input_data.chunk_type.name],  # Map GraphQL enum to shared enum
        text=input_data.text,
        image_url=input_data.image_url,
        image_data=input_data.image_data,
        equation=input_data.equation,
        table_data=input_data.table_data,
        code_content=input_data.code_content,
        code_language=input_data.code_language,
        chunk_metadata=input_data.chunk_metadata or {},
        position=input_data.position or {},
        size=input_data.size or {},
        vector_id=input_data.vector_id,
    )


@strawberry.type
class KnowledgeItemMutation:
    """知识条目变更操作"""

    @strawberry.mutation
    @handle_graphql_errors
    async def create_knowledge_item(self, input: KnowledgeItemCreateInput, info: Info) -> MutationResult:
        """创建知识条目"""
        logger.info(f"GraphQL mutation: create_knowledge_item for tenant: {input.tenant_id}")
        service = knowledge_item_service()
        create_dto = _convert_knowledge_item_input_to_dto(input)
        result = await service.create_item(create_dto)
        return MutationResult(
            success=True,
            message="知识条目创建成功",
            item_id=str(result.id),
        )

    @strawberry.mutation
    @handle_graphql_errors
    async def update_knowledge_item(self, item_id: str, input: KnowledgeItemUpdateInput, info: Info) -> MutationResult:
        """更新知识条目"""
        logger.info(f"GraphQL mutation: update_knowledge_item for item: {item_id}")
        service = knowledge_item_service()
        # Build update data, mapping GraphQL enums to shared enums
        update_data = {
            k: v
            for k, v in input.__dict__.items()
            if v is not None and k not in ["item_type", "status", "visibility"]
        }
        if input.item_type is not None:
            update_data["item_type"] = FileTypeEnum[input.item_type.name]
        if input.status is not None:
            update_data["status"] = StatusEnum[input.status.name]
        if input.visibility is not None:
            update_data["visibility"] = VisibilityEnum[input.visibility.name]
        update_dto = KnowledgeItemUpdateDTO(**update_data)
        result = await service.update_item(PydanticObjectId(item_id), update_dto)
        if result:
            return MutationResult(success=True, message="知识条目更新成功")
        raise NotFoundException("KnowledgeItem", item_id)

    @strawberry.mutation
    @handle_graphql_errors
    async def delete_knowledge_item(self, item_id: str, info: Info) -> MutationResult:
        """删除知识条目"""
        logger.info(f"GraphQL mutation: delete_knowledge_item for item: {item_id}")
        service = knowledge_item_service()
        success = await service.delete_item(PydanticObjectId(item_id))
        if success:
            return MutationResult(success=True, message="知识条目删除成功")
        raise NotFoundException("KnowledgeItem", item_id)

    @strawberry.mutation
    @handle_graphql_errors
    async def create_knowledge_item_with_infos(
        self, input: KnowledgeItemWithInfosCreateInput, info: Info
    ) -> KnowledgeItemWithInfosCreateResult:
        """创建知识条目及其关联信息"""
        logger.info(f"GraphQL mutation: create_knowledge_item_with_infos with {len(input.infos)} infos")
        service = knowledge_item_service()
        item_dto = _convert_knowledge_item_input_to_dto(input.item)
        info_dtos = [_convert_knowledge_item_info_input_to_dto(info_input) for info_input in input.infos]
        create_dto = KnowledgeItemWithInfosCreateDTO(item=item_dto, infos=info_dtos)
        item_result, infos_result = await service.create_item_with_infos(create_dto)
        item_schema = KnowledgeItemSchema(
            id=str(item_result.id),
            uid=item_result.uid,
            tenant_id=item_result.tenant_id,
            item_type=item_result.item_type,
            source_id=item_result.source_id,
            title=item_result.title,
            desc=item_result.desc,
            category=item_result.category,
            tags=item_result.tags,
            note=item_result.note,
            status=item_result.status,
            visibility=item_result.visibility,
            created_at=item_result.created_at,
            updated_at=item_result.updated_at,
            archived_at=item_result.archived_at,
            created_by=item_result.created_by,
            allowed_users=item_result.allowed_users,
            allowed_roles=item_result.allowed_roles,
            proc_meta=item_result.proc_meta,
            error_info=item_result.error_info,
            metadata=item_result.metadata,
        )
        info_schemas = [
            KnowledgeItemInfoSchema(
                id=str(info_result.id),
                uid=info_result.uid,
                tenant_id=info_result.tenant_id,
                master_id=info_result.master_id,
                page_idx=info_result.page_idx,
                page_size=info_result.page_size,
                preproc_blocks=info_result.preproc_blocks,
                para_blocks=info_result.para_blocks,
                discarded_blocks=info_result.discarded_blocks,
                note=info_result.note,
                created_at=info_result.created_at,
                updated_at=info_result.updated_at,
            )
            for info_result in infos_result
        ]
        return KnowledgeItemWithInfosCreateResult(
            success=True,
            message="知识条目及关联信息创建成功",
            item=item_schema,
            infos=info_schemas,
        )

    @strawberry.mutation
    @handle_graphql_errors
    async def chunk_knowledge_item(self, input: KnowledgeItemChunkingInput, info: Info) -> KnowledgeItemChunkingResult:
        """对知识条目进行切块操作"""
        logger.info(f"GraphQL mutation: chunk_knowledge_item with {len(input.chunks)} chunks")
        service = knowledge_item_service()
        chunk_dtos = [_convert_knowledge_item_chunk_input_to_dto(chunk_input) for chunk_input in input.chunks]
        chunking_dto = KnowledgeItemChunkingDTO(
            item_id=PydanticObjectId(input.item_id),
            chunks=chunk_dtos,
            update_metadata=input.update_metadata,
        )
        item_result, chunks_result = await service.chunk_item(chunking_dto)
        if not item_result:
            raise NotFoundException("KnowledgeItem", input.item_id)
        item_schema = KnowledgeItemSchema(
            id=str(item_result.id),
            uid=item_result.uid,
            tenant_id=item_result.tenant_id,
            item_type=item_result.item_type,
            source_id=item_result.source_id,
            title=item_result.title,
            desc=item_result.desc,
            category=item_result.category,
            tags=item_result.tags,
            note=item_result.note,
            status=item_result.status,
            visibility=item_result.visibility,
            created_at=item_result.created_at,
            updated_at=item_result.updated_at,
            archived_at=item_result.archived_at,
            created_by=item_result.created_by,
            allowed_users=item_result.allowed_users,
            allowed_roles=item_result.allowed_roles,
            proc_meta=item_result.proc_meta,
            error_info=item_result.error_info,
            metadata=item_result.metadata,
        )
        chunk_schemas = [
            KnowledgeItemChunkSchema(
                id=str(chunk_result.id),
                uid=chunk_result.uid,
                tenant_id=chunk_result.tenant_id,
                master_id=chunk_result.master_id,
                chunk_idx=chunk_result.chunk_idx,
                chunk_type=chunk_result.chunk_type,
                text=chunk_result.text,
                image_url=chunk_result.image_url,
                image_data=chunk_result.image_data,
                equation=chunk_result.equation,
                table_data=chunk_result.table_data,
                code_content=chunk_result.code_content,
                code_language=chunk_result.code_language,
                chunk_metadata=chunk_result.chunk_metadata,
                position=chunk_result.position,
                size=chunk_result.size,
                vector_id=chunk_result.vector_id,
                created_at=chunk_result.created_at,
                updated_at=chunk_result.updated_at,
            )
            for chunk_result in chunks_result
        ]
        return KnowledgeItemChunkingResult(
            success=True,
            message="知识条目切块成功",
            item=item_schema,
            chunks=chunk_schemas,
        )

    @strawberry.mutation
    @handle_graphql_errors
    async def delete_knowledge_item_with_related_data(self, item_id: str, info: Info) -> MutationResult:
        """删除知识条目及其所有关联数据"""
        logger.info(f"GraphQL mutation: delete_knowledge_item_with_related_data for item: {item_id}")
        service = knowledge_item_service()
        success = await service.delete_item_with_related_data(PydanticObjectId(item_id))
        if success:
            return MutationResult(success=True, message="知识条目及相关数据删除成功")
        raise NotFoundException("KnowledgeItem", item_id)

    @strawberry.mutation
    @handle_graphql_errors
    async def batch_delete_knowledge_items(self, input: BatchDeleteInput, info: Info) -> BatchOperationResult:
        """批量删除知识条目"""
        logger.info(f"GraphQL mutation: batch_delete_knowledge_items for {len(input.item_ids)} items")
        service = knowledge_item_service()
        item_ids = [PydanticObjectId(item_id) for item_id in input.item_ids]
        result = await service.batch_delete_items(item_ids)
        return BatchOperationResult(
            success=result.success,
            message=result.message,
            total_count=result.total_count,
            success_count=result.success_count,
            failed_count=result.failed_count,
            failed_items=result.failed_items,
        )


@strawberry.type
class KnowledgeItemQuery:
    """知识条目查询操作"""

    @strawberry.field
    @handle_graphql_errors
    async def knowledge_item(
        self, item_id: Optional[str] = None, uid: Optional[str] = None, tenant_id: Optional[str] = None, info: Info = None
    ) -> Optional[KnowledgeItemSchema]:
        """获取单个知识条目"""
        logger.debug(f"GraphQL query: knowledge_item - item_id: {item_id}, uid: {uid}, tenant: {tenant_id}")
        service = knowledge_item_service()
        if item_id:
            result = await service.get_item(PydanticObjectId(item_id))
        elif uid and tenant_id:
            result = await service.get_item_by_uid(uid, tenant_id)
        else:
            logger.warning("Either item_id or (uid and tenant_id) must be provided")
            return None
        if result:
            return KnowledgeItemSchema(
                id=str(result.id),
                uid=result.uid,
                tenant_id=result.tenant_id,
                item_type=result.item_type,
                source_id=result.source_id,
                title=result.title,
                desc=result.desc,
                category=result.category,
                tags=result.tags,
                note=result.note,
                status=result.status,
                visibility=result.visibility,
                created_at=result.created_at,
                updated_at=result.updated_at,
                archived_at=result.archived_at,
                created_by=result.created_by,
                allowed_users=result.allowed_users,
                allowed_roles=result.allowed_roles,
                proc_meta=result.proc_meta,
                error_info=result.error_info,
                metadata=result.metadata,
            )
        return None

    @strawberry.field
    @handle_graphql_errors
    async def knowledge_items(self, query: KnowledgeItemQueryInput, page: int = 1, size: int = 20, info: Info = None) -> KnowledgeItemPageInfo:
        """分页查询知识条目"""
        logger.info(f"GraphQL query: knowledge_items - page: {page}, size: {size}, tenant: {query.tenant_id}")
        service = knowledge_item_service()
        query_dto = KnowledgeItemQueryDTO(
            tenant_id=query.tenant_id,
            item_type=FileTypeEnum[query.item_type.name] if query.item_type else None,
            status=StatusEnum[query.status.name] if query.status else None,
            visibility=VisibilityEnum[query.visibility.name] if query.visibility else None,
            tags=query.tags,
            created_by=query.created_by,
        )
        skip = (page - 1) * size
        items = await service.query_items(query_dto, skip=skip, limit=size)
        total = await service.count_items(query_dto)
        item_schemas = [
            KnowledgeItemSchema(
                id=str(item.id),
                uid=item.uid,
                tenant_id=item.tenant_id,
                item_type=item.item_type,
                source_id=item.source_id,
                title=item.title,
                desc=item.desc,
                category=item.category,
                tags=item.tags,
                note=item.note,
                status=item.status,
                visibility=item.visibility,
                created_at=item.created_at,
                updated_at=item.updated_at,
                archived_at=item.archived_at,
                created_by=item.created_by,
                allowed_users=item.allowed_users,
                allowed_roles=item.allowed_roles,
                proc_meta=item.proc_meta,
                error_info=item.error_info,
                metadata=item.metadata,
            )
            for item in items
        ]
        return KnowledgeItemPageInfo(
            items=item_schemas,
            total=total,
            page=page,
            size=size,
            has_next=page * size < total,
            has_previous=page > 1,
        )

    @strawberry.field
    @handle_graphql_errors
    async def knowledge_item_with_details(
        self, query: KnowledgeItemWithDetailsQueryInput, info: Info
    ) -> Optional[KnowledgeItemWithDetailsSchema]:
        """获取知识条目及其关联数据"""
        logger.info(f"GraphQL query: knowledge_item_with_details for tenant: {query.tenant_id}")
        service = knowledge_item_service()
        query_dto = KnowledgeItemWithDetailsQueryDTO(
            item_id=PydanticObjectId(query.item_id) if query.item_id else None,
            uid=query.uid,
            tenant_id=query.tenant_id,
            include_infos=query.include_infos,
            include_chunks=query.include_chunks,
            info_page_idx=query.info_page_idx,
            chunk_types=[FileTypeEnum[ct.name] for ct in query.chunk_types] if query.chunk_types else None,
        )
        result = await service.get_item_with_details(query_dto)
        if not result.get("item"):
            return None
        item = result["item"]
        item_schema = KnowledgeItemSchema(
            id=str(item.id),
            uid=item.uid,
            tenant_id=item.tenant_id,
            item_type=item.item_type,
            source_id=item.source_id,
            title=item.title,
            desc=item.desc,
            category=item.category,
            tags=item.tags,
            note=item.note,
            status=item.status,
            visibility=item.visibility,
            created_at=item.created_at,
            updated_at=item.updated_at,
            archived_at=item.archived_at,
            created_by=item.created_by,
            allowed_users=item.allowed_users,
            allowed_roles=item.allowed_roles,
            proc_meta=item.proc_meta,
            error_info=item.error_info,
            metadata=item.metadata,
        )
        info_schemas = [
            KnowledgeItemInfoSchema(
                id=str(info.id),
                uid=info.uid,
                tenant_id=info.tenant_id,
                master_id=info.master_id,
                page_idx=info.page_idx,
                page_size=info.page_size,
                preproc_blocks=info.preproc_blocks,
                para_blocks=info.para_blocks,
                discarded_blocks=info.discarded_blocks,
                note=info.note,
                created_at=info.created_at,
                updated_at=info.updated_at,
            )
            for info in result.get("infos", [])
        ]
        chunk_schemas = [
            KnowledgeItemChunkSchema(
                id=str(chunk.id),
                uid=chunk.uid,
                tenant_id=chunk.tenant_id,
                master_id=chunk.master_id,
                chunk_idx=chunk.chunk_idx,
                chunk_type=chunk.chunk_type,
                text=chunk.text,
                image_url=chunk.image_url,
                image_data=chunk.image_data,
                equation=chunk.equation,
                table_data=chunk.table_data,
                code_content=chunk.code_content,
                code_language=chunk.code_language,
                chunk_metadata=chunk.chunk_metadata,
                position=chunk.position,
                size=chunk.size,
                vector_id=chunk.vector_id,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at,
            )
            for chunk in result.get("chunks", [])
        ]
        return KnowledgeItemWithDetailsSchema(
            item=item_schema,
            infos=info_schemas,
            chunks=chunk_schemas,
        )


@strawberry.type
class Query:
    knowledge_items: KnowledgeItemQuery = strawberry.field(resolver=KnowledgeItemQuery)


@strawberry.type
class Mutation:
    knowledge_items: KnowledgeItemMutation = strawberry.field(resolver=KnowledgeItemMutation)


schema = strawberry.Schema(query=Query, mutation=Mutation)