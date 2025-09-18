# -*- coding: utf-8 -*-
# Knowledge processing service for handling knowledge items with Weaviate and Neo4j integration

from datetime import datetime
import json
from typing import Dict, Any, Optional
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings
from foxmask.utils.helpers import generate_uuid,convert_objectids_to_strings

from foxmask.core.model import Visibility
from foxmask.knowledge.models import (
   KnowledgeItem,
   ItemContentTypeEnum,
   KnowledgeItemStatusEnum,
   KnowledgeItemTypeEnum
)    
from foxmask.file.repositories import file_repository
from foxmask.knowledge.repositories import (
    knowledge_item_repository,knowledge_item_content_repository
)    
from foxmask.task.message import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    KnowledgeProcessingMessage
)    

from .knowledge_item import knowledge_item_service
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
        logger.info(f"_process_create_from_file:{message}")
        """Process a knowledge item creation request from a file"""
        file_id = message.get("key")
        if not file_id:
            logger.error("Missing file_id in knowledge item creation message")
            return
        
        try:
            # 获取文件对象
            file = await file_repository.get_file_by_file_id(file_id)
            if not file:
                logger.error(f"File not found with file_id: {file_id}")
                return
            
            # 创建知识条目
            item_data = {
                "title": file.filename,
                "description": file.description,
                "tags": ["FILE"],
                "category": "File",
                "metadata": {},
                "tenant_id": file.tenant_id,
                "visibility": file.visibility,
                "allowed_users": file.allowed_users,
                "allowed_roles": file.allowed_roles,
                "created_by": file.uploaded_by,
                "item_type": KnowledgeItemTypeEnum.FILE,
                "status": KnowledgeItemStatusEnum.CREATED,
                "content": {
                    "source": [{
                        "content_id":"",
                        "file_id": file_id, 
                        "filename": file.filename, 
                        "bucket_name": file.minio_bucket,
                        "object_name": file.minio_object_name,
                        "created_at": file.created_at
                    }]
                },
                "processing_metadata": {},
            }
            
            # 创建知识条目
            item = await knowledge_item_repository.create_item(item_data)
            
            # 创建知识项内容
            item_content = {
                "title": file.filename,
                "description": file.description,
                "tags": ["FILE"],
                "category": "File",
                "tenant_id": file.tenant_id,
                "item_id": convert_objectids_to_strings(item.id),
                "content_type": ItemContentTypeEnum.SOURCE,
                "content_data": file.model_dump() , # 使用 model_dump() 而不是 to_dict()
                "created_by":file.uploaded_by
            }
            
            content = await knowledge_item_content_repository.create_content(item_content)
            logger.info(f"Knowledge item created from file {file_id}: {item.id}")
            
            # 可选：触发进一步处理（解析、向量化、图谱化）
            processing_message = {
                "item_id": item.id,
                "type": MessageEventTypeEnum.PARSE_MD_FROM_SOURCE
            }
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item.id
            )
            
            processing_message = {
                "type": MessageEventTypeEnum.PARSE_JSON_FROM_SOURCE,
                "item_id": item.id,
                "tenant_id": item.tenant_id,
            }
            await kafka_manager.send_message(
                topic=MessageTopicEnum.KB_PROCESSING,
                value=processing_message,
                key=item.id
            )
            logger.info(f"Processing message sent for knowledge item {item.id}")
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from file {file_id}: {e}")
            # 可以考虑添加更详细的错误处理和重试逻辑       

    async def _parse_content(self, knowledge_item: KnowledgeItem):
        """Parse knowledge item content"""
        logger.info(f"Parsing content for knowledge item: {knowledge_item.id}")
        
        # Simulate parsing - in real implementation, this would extract text from files, webpages, etc.
        knowledge_item.parsed_content = {
            "content": f"Parsed content for {knowledge_item.title}",
            "metadata": {
                "source_urls": knowledge_item.source_urls,
                "file_ids": knowledge_item.file_ids,
                "parsed_at": datetime.utcnow().isoformat()
            }
        }
        
        knowledge_item.update_status(KnowledgeItemStatusEnum.PARSED)
        await knowledge_item.save()

    async def _process_create_from_chat(self, message: Dict[str, Any]):
        logger.info(f"_process_create_from_chat:{message}")
     
        
    async def _process_parse_md_from_source(self, message: Dict[str, Any]):
        logger.info(f"_process_parse_md_from_source:{message}")

        item_id = message.get("key","")
        data_value = message.get('value', {})
        tenant_id = data_value.get('tenant_id',"")
        #2、调用解析服务
        await knowledge_parser_service.parse_knowledge_item_to_md(item_id,tenant_id)
        #4、触发下一步指令
   

    async def _process_parse_json_from_source(self, message: Dict[str, Any]):
        logger.info(f"_process_parse_json_from_source:{message}")
        item_id = message.get("key","")
        data_value = message.get('value', {})
        tenant_id = data_value.get('tenant_id',"")
        #1、解析开始
        await knowledge_item_repository.update_item_status(item_id,tenant_id,KnowledgeItemStatusEnum.PARSING)
        #2、调用解析服务
        await knowledge_parser_service.parse_knowledge_item_to_json(item_id,tenant_id)
        #3、修改状态
        await knowledge_item_repository.update_item_status(item_id,tenant_id,KnowledgeItemStatusEnum.PARSED)
        #4、触发下一步指令
   
    async def _process_vectorized_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_vectorized_knowledge:{message}")

    async def _process_graph_knowledge(self, message: Dict[str, Any]):
        logger.info(f"_process_graph_knowledge:{message}")

    async def _handle_unknown_event_type(self, message: Dict[str, Any]):
        logger.info(f"_handle_unknown_event_type:{message}")


    async def _vectorize_content(self, knowledge_item: KnowledgeItem):
        """Vectorize knowledge item content and index in Weaviate"""
        if not knowledge_item.parsed_content:
            logger.warning(f"No parsed content for vectorization: {knowledge_item.id}")
            return
        
        logger.info(f"Vectorizing content for knowledge item: {knowledge_item.id}")
        
        try:
            # Index in Weaviate
            weaviate_id = await vector_search_service.index_knowledge_item({
                "id": str(knowledge_item.id),
                "title": knowledge_item.title,
                "description": knowledge_item.description,
                "parsed_content": knowledge_item.parsed_content,
                "type": knowledge_item.type,
                "tags": knowledge_item.tags,
                "category": knowledge_item.category,
                "status": knowledge_item.status.value,
                "created_by": knowledge_item.created_by,
                "created_at": knowledge_item.created_at,
                "updated_at": knowledge_item.updated_at
            })
            
            if weaviate_id:
                knowledge_item.vector_id = weaviate_id
                knowledge_item.update_status(KnowledgeItemStatusEnum.VECTORIZED)
                await knowledge_item.save()
                
                logger.info(f"Content vectorized for knowledge item: {knowledge_item.id}")
            else:
                raise Exception("Failed to index in Weaviate")
            
        except Exception as e:
            logger.error(f"Error vectorizing content for {knowledge_item.id}: {e}")
            raise

    async def _create_graph_relations(self, knowledge_item: KnowledgeItem):
        """Create graph relations in Neo4j"""
        logger.info(f"Creating graph relations for knowledge item: {knowledge_item.id}")
        
        try:
            # Create node in Neo4j
            neo4j_id = await knowledge_graph_service.create_knowledge_item_node({
                "id": str(knowledge_item.id),
                "title": knowledge_item.title,
                "description": knowledge_item.description,
                "type": knowledge_item.type,
                "status": knowledge_item.status.value,
                "category": knowledge_item.category,
                "created_by": knowledge_item.created_by,
                "created_at": knowledge_item.created_at,
                "updated_at": knowledge_item.updated_at,
                "knowledge_base_ids": knowledge_item.knowledge_base_ids,
                "tags": knowledge_item.tags
            })
            
            if neo4j_id:
                knowledge_item.graph_id = neo4j_id
                knowledge_item.update_status(KnowledgeItemStatusEnum.COMPLETED)
                await knowledge_item.save()
                
                logger.info(f"Graph relations created for knowledge item: {knowledge_item.id}")
            else:
                raise Exception("Failed to create graph relations")
            
        except Exception as e:
            logger.error(f"Error creating graph relations for {knowledge_item.id}: {e}")
            raise

knowledge_processing_service = KnowledgeProcessingService()