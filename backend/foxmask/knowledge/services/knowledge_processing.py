# -*- coding: utf-8 -*-
# Knowledge processing service for handling knowledge items with Weaviate and Neo4j integration

from datetime import datetime
import json
from typing import Dict, Any, Optional
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings
from foxmask.utils.helpers import generate_uuid,convert_objectids_to_strings

from foxmask.core.model import Visibility,Status
from foxmask.knowledge.models import (
    KnowledgeItemTypeEnum,
    ItemChunkTypeEnum,
    KnowledgeItem,
    KnowledgeItemInfo,
    KnowledgeItemChunk
)    
from foxmask.file.repositories import get_repository_manager
from foxmask.knowledge.repositories import (
    knowledge_item_repository,
    knowledge_item_info_repository,
    knowledge_item_chunk_repository
)    
from foxmask.task.message import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    KnowledgeProcessingMessage
)    

from .knowledge_item import knowledge_item_service
from .knowledge_graph import knowledge_graph_service
from .vector_search import vector_search_service

class KnowledgeProcessingService:
    def __init__(self):
        self.file_repository = get_repository_manager().file_repository
        pass
    
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
        logger.info(f"_process_create_from_file:{message}")
        """Process a knowledge item creation request from a file"""
        try:
            file_id = message.get("key")
            if not file_id:
                raise Exception("文件ID无效：file_id")
            data_value = message.get('value', {})
            if not isinstance(data_value, dict):
                raise Exception(f"无效数据(data_value),file_id={file_id}")
                
            tenant_id = data_value.get('tenant_id',"foxmask")
            if tenant_id is None:
                raise Exception(f"租户ID无效(tenant_id),file_id={file_id}")
            
            item, _ = await knowledge_item_service.create_item_from_file(tenant_id=tenant_id,file_id=file_id)

            # 触发进一步处理
            processing_message = {
                "item_id": item.uid,
                "tenant_id": item.tenant_id,
                "type": MessageEventTypeEnum.PARSE_MD_FROM_SOURCE.value,
            }
            
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item.uid
            )
            
            return {
                "status": "success",
                "tenant_id": item.tenant_id,
                "file_id": file_id,
                "item_id": item.uid,
            }
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from file: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to create knowledge item from file"
            }

    async def _process_create_from_chat(self, message: Dict[str, Any]):
        logger.info(f"_process_create_from_chat:{message}")
     
    async def _process_parse_md_from_source(self, message: Dict[str, Any]):
        logger.info(f"_process_parse_md_from_source:{message}")
      
        try:
            item_id = message.get("key")
            if not item_id:
                raise Exception("知识条目UID无效：item_id")
            data_value = message.get('value', {})
            if not isinstance(data_value, dict):
                raise Exception(f"无效数据(data_value),item_id={item_id}")
                
            tenant_id = data_value.get('tenant_id',"foxmask")
            if tenant_id is None:
                raise Exception(f"租户ID无效(tenant_id),item_id={item_id}")
            
            item = await knowledge_item_service.parse_item_info_to_markdown(tenant_id=tenant_id,item_id=item_id)
            return "OK" 
            # 触发进一步处理
            processing_message = {
                "item_id": item.uid,
                "tenant_id": item.tenant_id,
                "type": MessageEventTypeEnum.VECTORIZED_KNOWLEDGE.value,
            }
            
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item.uid
            )
            
            return {
                "status": "success",
                "tenant_id": item.tenant_id,
                "item_id": item.uid,
            }
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from file: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to create knowledge item from file"
            }      
        
    async def _process_vectorized_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_vectorized_knowledge:{message}")

    async def _process_graph_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_graph_knowledge:{message}")

    async def _handle_unknown_event_type(self, message: Dict[str, Any]):
        logger.info(f"_handle_unknown_event_type:{message}")

knowledge_processing_service = KnowledgeProcessingService()