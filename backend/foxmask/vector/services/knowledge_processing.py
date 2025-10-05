# -*- coding: utf-8 -*-
# Knowledge processing service for handling knowledge items with Weaviate and Neo4j integration

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings

from foxmask.knowledge_item.domain import (
    KnowledgeItemEntity, KnowledgeItemContentEntity,
    KnowledgeItemStatusEnum, KnowledgeItemTypeEnum, ItemContentTypeEnum
)
from foxmask.knowledge_item.dto import (
    KnowledgeItemCreateDTO, KnowledgeItemContentCreateDTO,
    KnowledgeItemWithContentsCreateDTO,
    KnowledgeItemUpdateDTO, FileProcessingRequestDTO
)
from foxmask.knowledge_item.services import knowledge_item_service
from foxmask.file.repositories import file_repository

from foxmask.task.message import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    KnowledgeProcessingMessage
)    

from .knowledge_graph import knowledge_graph_service
from .vector_search import vector_search_service
from .knowledge_parser import knowledge_parser_service

class KnowledgeProcessingService:
    
    async def process_knowledge(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a knowledge item with Weaviate and Neo4j integration.
        
        Args:
            message: Input message dictionary containing event data.
            
        Returns:
            Optional[Dict[str, Any]]: Result of processing or error response.
        """
        # 获取 data_value，检查是否为字典
        data_value = message.get('value', {})
        if not isinstance(data_value, dict):
            logger.error(f"Invalid data_value, expected dict, got {type(data_value)}: {message}")
            return {
                "status": "error",
                "event_type": "unknown",
                "error": "Invalid data_value type",
                "message": "data_value must be a dictionary"
            }

        # 获取 event_type，转换为字符串并规范化
        event_type = data_value.get('type')
        if event_type is None:
            logger.error(f"Missing event_type in message: {message}")
            return {
                "status": "error",
                "event_type": "unknown",
                "error": "Missing event_type",
                "message": "Event type is required"
            }

        # 转换为字符串并清理
        event_type = str(event_type).strip().lower()
        # 尝试将 event_type 转换为 MessageEventTypeEnum
        try:
            event_type_enum = MessageEventTypeEnum(event_type)
        except ValueError:
            logger.error(f"Invalid event_type: '{event_type}', valid types: {[e.value for e in MessageEventTypeEnum]}")
            return await self._handle_unknown_event_type(message)

        # 使用 match-case 处理事件类型
        try:
            match event_type_enum:
                case MessageEventTypeEnum.CREATE_ITEM_FROM_FILE:
                    return await self._process_create_from_file(message)
                case MessageEventTypeEnum.CREATE_ITEM_FROM_CHAT:
                    return await self._process_create_from_chat(message)
                case MessageEventTypeEnum.PARSE_MD_FROM_SOURCE:
                    return await self._process_parse_md_from_source(message)
                case MessageEventTypeEnum.PARSE_JSON_FROM_SOURCE:
                    return await self._process_parse_json_from_source(message)
                case MessageEventTypeEnum.VECTORIZED_KNOWLEDGE:
                    return await self._process_vectorized_knowledge(message)
                case MessageEventTypeEnum.GRAPH_KNOWLEDGE:
                    return await self._process_graph_knowledge(message)
                case _:
                    logger.error(f"Unexpected event_type_enum: {event_type_enum}")
                    return await self._handle_unknown_event_type(message)

        except ValueError as ve:
            logger.error(f"ValueError processing event_type '{event_type}': {str(ve)}")
            return {
                "status": "error",
                "event_type": event_type,
                "error": str(ve),
                "message": f"Failed to process event type: {event_type}"
            }
        except Exception as e:
            logger.error(f"Unexpected error processing event_type '{event_type}': {str(e)}", exc_info=True)
            return {
                "status": "error",
                "event_type": event_type,
                "error": str(e),
                "message": f"Unexpected error processing event type: {event_type}"
            }
    
    async def _process_create_from_file(self, message: Dict[str, Any]):
        file_id = message.get("key")
        if not file_id:
            logger.error("Missing file_id in knowledge item creation message")
            return
        data_value = message.get('value', {})
        if not isinstance(data_value, dict):
            logger.error(f"Invalid data_value, expected dict, got {type(data_value)}: {message}")
            return {
                "status": "error",
                "event_type": "unknown",
                "error": "Invalid data_value type",
                "message": "data_value must be a dictionary"
            }
            
        tenant_id = data_value.get('tenant_id',"foxmask")
        if tenant_id is None:
            logger.error(f"Missing tenant_id in message: {message}")
            return {
                "status": "error",
                "event_type": "unknown",
                "error": "Missing tenant_id",
                "message": "tenant_id is required"
            }
        
        # 获取文件对象
        file = await file_repository.get_file_by_file_id(file_id)
        if not file:
            logger.error(f"File not found with file_id: {file_id}")
            return
        
        return await knowledge_parser_service.parse_file_to_item_md(tenant_id=tenant_id,file_id=file_id)
    
    async def _process_create_from_chat(self, message: Dict[str, Any]):
        logger.info(f"_process_create_from_chat:{message}")
        # 实现聊天创建知识条目的逻辑
        try:
            data_value = message.get('value', {})
            chat_data = data_value.get('chat_data', {})
            
            # 创建知识条目DTO
            item_create_dto = KnowledgeItemCreateDTO(
                item_type=KnowledgeItemTypeEnum.CHAT,
                title=chat_data.get('title', 'Chat Conversation'),
                description=chat_data.get('description', ''),
                metadata=chat_data.get('metadata', {}),
                tags=chat_data.get('tags', ['CHAT']),
                tenant_id=data_value.get('tenant_id'),
                visibility=data_value.get('visibility', 'private'),
                created_by=data_value.get('created_by'),
                allowed_users=data_value.get('allowed_users', []),
                allowed_roles=data_value.get('allowed_roles', [])
            )
            
            # 创建知识条目
            item_dto = await knowledge_item_service.create_knowledge_item(item_create_dto)
            
            # 创建知识内容
            content_create_dto = KnowledgeItemContentCreateDTO(
                item_id=item_dto.item_id,
                content_type=ItemContentTypeEnum.SOURCE,
                content_data=chat_data,
                metadata={
                    "processing_timestamp": datetime.now().isoformat()
                },
                created_by=data_value.get('created_by')
            )
            
            content_dto = await knowledge_item_service.add_content_to_item(content_create_dto)
            
            logger.info(f"Knowledge item created from chat: {item_dto.id}")
            
            # 触发进一步处理
            processing_message = {
                "item_id": str(item_dto.id),
                "item_id": item_dto.item_id,
                "type": MessageEventTypeEnum.PARSE_JSON_FROM_SOURCE.value,
                "tenant_id": item_dto.tenant_id
            }
            
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=str(item_dto.id)
            )
            
            return {
                "status": "success",
                "item_id": str(item_dto.id),
                "item_id": item_dto.item_id,
                "content_id": str(content_dto.id)
            }
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from chat: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to create knowledge item from chat"
            }
        
    async def _process_parse_md_from_source(self, message: Dict[str, Any]):
        logger.info(f"_process_parse_md_from_source:{message}")

        try:
            item_id = message.get("key", "")
            data_value = message.get('value', {})
            item_id = data_value.get('item_id', "")
            tenant_id = data_value.get('tenant_id', "")
            
            if not item_id or not item_id:
                logger.error(f"Missing item_id or item_id in message: {message}")
                return {
                    "status": "error",
                    "error": "Missing item_id or item_id",
                    "message": "Item ID and Knowledge Item ID are required"
                }
            
            # 更新状态为解析中
            await knowledge_item_service.update_knowledge_item(
                UUID(item_id),
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.PARSING)
            )
            
            # 调用解析服务
            await knowledge_parser_service.parse_knowledge_item_to_md(item_id, tenant_id)
            
            # 更新状态为已解析
            await knowledge_item_service.update_knowledge_item(
                UUID(item_id),
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.PARSED)
            )
            
            # 触发向量化处理
            '''
            processing_message = {
                "item_id": item_id,
                "item_id": item_id,
                "type": MessageEventTypeEnum.VECTORIZED_KNOWLEDGE.value,
                "tenant_id": tenant_id
            }
            
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item_id
            )
            '''
            
            
            logger.info(f"MD parsing completed for knowledge item {item_id}")
            
            return {
                "status": "success",
                "item_id": item_id,
                "message": "MD parsing completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing MD parsing: {e}", exc_info=True)
            # 更新状态为失败
            try:
                await knowledge_item_service.update_knowledge_item(
                    UUID(item_id),
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.FAILED)
                )
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to process MD parsing"
            }

    async def _process_parse_json_from_source(self, message: Dict[str, Any]):
        logger.info(f"_process_parse_json_from_source:{message}")
        
        try:
            item_id = message.get("key", "")
            data_value = message.get('value', {})
            item_id = data_value.get('item_id', "")
            tenant_id = data_value.get('tenant_id', "")
            
            if not item_id or not item_id:
                logger.error(f"Missing item_id or item_id in message: {message}")
                return {
                    "status": "error",
                    "error": "Missing item_id or item_id",
                    "message": "Item ID and Knowledge Item ID are required"
                }
            
            # 更新状态为解析中
            await knowledge_item_service.update_knowledge_item(
                UUID(item_id),
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.PARSING)
            )
            
            # 调用解析服务
            await knowledge_parser_service.parse_knowledge_item_to_json(item_id, item_id, tenant_id)
            
            # 更新状态为已解析
            await knowledge_item_service.update_knowledge_item(
                UUID(item_id),
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.PARSED)
            )
            
            # 触发向量化处理
            processing_message = {
                "item_id": item_id,
                "item_id": item_id,
                "type": MessageEventTypeEnum.VECTORIZED_KNOWLEDGE.value,
                "tenant_id": tenant_id
            }
            
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item_id
            )
            
            logger.info(f"JSON parsing completed for knowledge item {item_id}")
            
            return {
                "status": "success",
                "item_id": item_id,
                "message": "JSON parsing completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing JSON parsing: {e}", exc_info=True)
            # 更新状态为失败
            try:
                await knowledge_item_service.update_knowledge_item(
                    UUID(item_id),
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.FAILED)
                )
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to process JSON parsing"
            }

    async def _process_vectorized_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_vectorized_knowledge:{message}")
        
        try:
            item_id = message.get("key", "")
            data_value = message.get('value', {})
            item_id = data_value.get('item_id', "")
            tenant_id = data_value.get('tenant_id', "")
            
            if not item_id or not item_id:
                logger.error(f"Missing item_id or item_id in message: {message}")
                return {
                    "status": "error",
                    "error": "Missing item_id or item_id",
                    "message": "Item ID and Knowledge Item ID are required"
                }
            
            # 更新状态为向量化中
            await knowledge_item_service.update_knowledge_item(
                item_id,
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.VECTORIZING)
            )
            
            # 获取知识条目和内容
            item_dto = await knowledge_item_service.get_knowledge_item(item_id)
            if not item_dto:
                raise ValueError(f"Knowledge item not found: {item_id}")
            
            contents = await knowledge_item_service.get_item_contents(item_id)
            
            # 准备向量化数据 - 根据 VectorSearchService 的要求格式
            knowledge_item_data = {
                "id": item_dto.item_id,
                "title": item_dto.title,
                "description": item_dto.description or "",
                "type": item_dto.item_type.value,
                "tags": item_dto.tags,
                "status": item_dto.status.value,
                "created_by": item_dto.created_by or "",
                "created_at": item_dto.created_at,
                "updated_at": item_dto.updated_at,
                # 从内容中提取解析后的内容
                "parsed_content": self._extract_parsed_content(contents)
            }
            
            # 调用向量化服务 - 现在只传递一个参数
            vectorized = await vector_search_service.index_knowledge_item(knowledge_item_data)
            
            if vectorized:
                # 更新状态为已向量化
                await knowledge_item_service.update_knowledge_item(
                    item_id,
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.VECTORIZED)
                )
                
                # 触发图谱化处理
                processing_message = {
                    "item_id": item_id,
                    "item_id": item_id,
                    "type": MessageEventTypeEnum.GRAPH_KNOWLEDGE.value,
                    "tenant_id": tenant_id
                }
                
                await kafka_manager.send_message(
                    topic=MessageTopicEnum.KB_PROCESSING,
                    value=processing_message,
                    key=item_id
                )
                
                logger.info(f"Vectorization completed for knowledge item {item_id}")
                
                return {
                    "status": "success",
                    "item_id": item_id,
                    "message": "Vectorization completed"
                }
            else:
                raise Exception("Vectorization failed")
            
        except Exception as e:
            logger.error(f"Error processing vectorization: {e}", exc_info=True)
            # 更新状态为失败
            try:
                await knowledge_item_service.update_knowledge_item(
                    item_id,
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.FAILED)
                )
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to process vectorization"
            }

    def _extract_parsed_content(self, contents: List) -> Dict[str, Any]:
        """从内容列表中提取解析后的内容"""
        parsed_content = {"content": ""}
        
        for content in contents:
            if hasattr(content, 'content_data') and isinstance(content.content_data, dict):
                content_data = content.content_data
                # 查找解析后的内容
                if 'parsed_content' in content_data:
                    parsed_content = content_data['parsed_content']
                    break
                elif 'content' in content_data:
                    parsed_content['content'] = content_data['content']
                    break
            elif hasattr(content, 'content_data') and isinstance(content.content_data, str):
                parsed_content['content'] = content.content_data
                break
        
        return parsed_content
    async def _process_graph_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_graph_knowledge:{message}")
        
        try:
            item_id = message.get("key", "")
            data_value = message.get('value', {})
            item_id = data_value.get('item_id', "")
            tenant_id = data_value.get('tenant_id', "")
            
            if not item_id or not item_id:
                logger.error(f"Missing item_id or item_id in message: {message}")
                return {
                    "status": "error",
                    "error": "Missing item_id or item_id",
                    "message": "Item ID and Knowledge Item ID are required"
                }
            
            # 更新状态为图谱化中
            await knowledge_item_service.update_knowledge_item(
                UUID(item_id),
                KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.GRAPHING)
            )
            
            # 获取知识条目和内容
            item_dto = await knowledge_item_service.get_knowledge_item(UUID(item_id))
            if not item_dto:
                raise ValueError(f"Knowledge item not found: {item_id}")
            
            contents = await knowledge_item_service.get_item_contents(UUID(item_id))
            
            # 调用图谱服务
            graphed = await knowledge_graph_service.create_knowledge_item_node(
                item_dto, contents, tenant_id
            )
            
            if graphed:
                # 更新状态为已完成
                await knowledge_item_service.update_knowledge_item(
                    UUID(item_id),
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.COMPLETED)
                )
                
                logger.info(f"Graph processing completed for knowledge item {item_id}")
                
                return {
                    "status": "success",
                    "item_id": item_id,
                    "message": "Graph processing completed"
                }
            else:
                raise Exception("Graph processing failed")
            
        except Exception as e:
            logger.error(f"Error processing graph: {e}", exc_info=True)
            # 更新状态为失败
            try:
                await knowledge_item_service.update_knowledge_item(
                    UUID(item_id),
                    KnowledgeItemUpdateDTO(status=KnowledgeItemStatusEnum.FAILED)
                )
            except Exception:
                pass
            
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to process graph"
            }

    async def _handle_unknown_event_type(self, message: Dict[str, Any]):
        logger.info(f"_handle_unknown_event_type:{message}")
        return {
            "status": "error",
            "event_type": "unknown",
            "error": "Unknown event type",
            "message": f"Unknown event type in message: {message}"
        }

knowledge_processing_service = KnowledgeProcessingService()