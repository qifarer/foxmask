# graphql/schema.py
import strawberry
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from foxmask.knowledge_item.dto import (
    KnowledgeItemCreateDTO, KnowledgeItemUpdateDTO, KnowledgeItemContentCreateDTO,
    SearchFiltersDTO, FileProcessingRequestDTO
)
from foxmask.knowledge_item.services import knowledge_item_service
from foxmask.knowledge_item.domain import (
    KnowledgeItemTypeEnum, KnowledgeItemStatusEnum, ItemContentTypeEnum
)
from .schemas import (
    KnowledgeItemContentType,KnowledgeItemType,
    KnowledgeItemWithContentsType,SearchResultType,FileProcessingResultType,
    KnowledgeItemCreateInput,KnowledgeItemUpdateInput,
    KnowledgeItemContentCreateInput,SearchFiltersInput,
    FileProcessingRequestInput
)

@strawberry.type
class KnowledgeItemQuery:
    @strawberry.field
    async def get_knowledge_item(self, item_id: UUID) -> Optional[KnowledgeItemType]:
        """获取知识条目"""
        item_dto = await knowledge_item_service.get_knowledge_item(item_id)
        if item_dto:
            # 将DTO转换为GraphQL类型
            return KnowledgeItemType(**item_dto.dict())
        return None
    
    @strawberry.field
    async def search_knowledge(
        self,
        query: str,
        filters: Optional[SearchFiltersInput] = None,
        limit: int = 10
    ) -> SearchResultType:
        """搜索知识条目"""
        # 将输入转换为DTO
        filters_dto = None
        if filters:
            filters_dto = SearchFiltersDTO(**filters.__dict__)
        
        # 调用Service
        result_dto = await knowledge_item_service.semantic_search(query, filters_dto, limit)
        
        # 将DTO转换为GraphQL类型
        items = []
        for item in result_dto.items:
            item_type = KnowledgeItemType(**item.item.dict())
            content_types = [KnowledgeItemContentType(**content.dict()) for content in item.contents]
            items.append(KnowledgeItemWithContentsType(item=item_type, contents=content_types))
        
        return SearchResultType(
            items=items,
            total_count=result_dto.total_count,
            search_time=result_dto.search_time
        )

@strawberry.type
class KnowledgeItemMutation:
    @strawberry.mutation
    async def create_knowledge_item(self, input: KnowledgeItemCreateInput) -> KnowledgeItemType:
        """创建知识条目"""
        # 将输入转换为DTO
        create_dto = KnowledgeItemCreateDTO(**input.__dict__)
        
        # 调用Service
        item_dto = await knowledge_item_service.create_knowledge_item(create_dto)
        
        # 将DTO转换为GraphQL类型
        return KnowledgeItemType(**item_dto.dict())
    
    @strawberry.mutation
    async def update_knowledge_item(
        self,
        item_id: UUID,
        input: KnowledgeItemUpdateInput
    ) -> Optional[KnowledgeItemType]:
        """更新知识条目"""
        # 将输入转换为DTO
        update_dto = KnowledgeItemUpdateDTO(**input.__dict__)
        
        # 调用Service
        item_dto = await knowledge_item_service.update_knowledge_item(item_id, update_dto)
        
        # 将DTO转换为GraphQL类型
        if item_dto:
            return KnowledgeItemType(**item_dto.dict())
        return None
    
    @strawberry.mutation
    async def delete_knowledge_item(self, item_id: UUID) -> bool:
        """删除知识条目"""
        return await knowledge_item_service.delete_knowledge_item(item_id)
    
    @strawberry.mutation
    async def add_content_to_item(self, input: KnowledgeItemContentCreateInput) -> KnowledgeItemContentType:
        """添加内容到知识条目"""
        # 将输入转换为DTO
        content_dto = KnowledgeItemContentCreateDTO(**input.__dict__)
        
        # 调用Service
        content_result = await knowledge_item_service.add_content_to_item(content_dto)
        
        # 将DTO转换为GraphQL类型
        return KnowledgeItemContentType(**content_result.dict())
    
    @strawberry.mutation
    async def process_file(self, input: FileProcessingRequestInput) -> FileProcessingResultType:
        """处理文件"""
        # 将输入转换为DTO
        request_dto = FileProcessingRequestDTO(**input.__dict__)
        
        # 调用Service
        result_dto = await knowledge_item_service.process_file(request_dto)
        
        # 将DTO转换为GraphQL类型
        return FileProcessingResultType(**result_dto.dict())

