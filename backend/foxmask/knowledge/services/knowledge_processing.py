# -*- coding: utf-8 -*-
# Knowledge processing service for handling knowledge items with Weaviate and Neo4j integration

from datetime import datetime
import json
from typing import Dict, Any
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings
from foxmask.utils.helpers import generate_uuid

from ..models.knowledge_item import KnowledgeItem, KnowledgeItemStatus,KnowledgeItemType
from .knowledge_graph import knowledge_graph_service
from .vector_search import vector_search_service

class KnowledgeProcessingService:
    async def process_knowledge_item_from_file(self, message: Dict[str, Any]):
        """Process a knowledge item creation request from a file"""
        file_id = message.get("file_id")
        if not file_id:
            logger.error("Missing file_id in knowledge item creation message")
            return
        
        try:
            # Create knowledge item from file metadata
            knowledge_item = KnowledgeItem(
                title=message.get("title", f"Knowledge Item from File {file_id}"),
                description=message.get("description", ""),
                type=KnowledgeItemType.FILE,
                status=KnowledgeItemStatus.PENDING,
                source_urls=message.get("source_urls", []),
                file_ids=[file_id],
                tags=message.get("tags", []),
                category=message.get("category", "general"),
                created_by=message.get("created_by", "system"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await knowledge_item.insert()
            
            logger.info(f"Knowledge item created from file {file_id}: {knowledge_item.id}")
            
            #id =  generate_uuid()
            # Optionally, trigger further processing (parsing, vectorization, graphing)
            #processing_message = {
            #    "knowledge_item_id": id,
            #    "process_types": ["parse", "vectorize", "graph"]
            #}
            #await kafka_manager.send_message(
            #    topic=settings.KAFKA_KNOWLEDGE_TOPIC,
            #    value=processing_message,
            #    key=id
            #)
            #logger.info(f"Processing message sent for knowledge item {id}")
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from file {file_id}: {e}")
    
    async def process_knowledge_item(self, message: Dict[str, Any]):
        """Process a knowledge item with Weaviate and Neo4j integration"""
        knowledge_item_id = message.get("knowledge_item_id")
        process_types = message.get("process_types", [])
        
        if not knowledge_item_id:
            logger.error("Missing knowledge_item_id in processing message")
            return
        
        # Get knowledge item
        knowledge_item = await KnowledgeItem.get(knowledge_item_id)
        if not knowledge_item:
            logger.error(f"Knowledge item not found: {knowledge_item_id}")
            return
        
        try:
            # Update status to processing
            knowledge_item.update_status(KnowledgeItemStatus.PROCESSING)
            await knowledge_item.save()
            
            # Perform processing based on types
            if "parse" in process_types:
                await self._parse_content(knowledge_item)
            
            if "vectorize" in process_types:
                await self._vectorize_content(knowledge_item)
            
            if "graph" in process_types:
                await self._create_graph_relations(knowledge_item)
            
            # Update status to completed
            knowledge_item.update_status(KnowledgeItemStatus.COMPLETED)
            await knowledge_item.save()
            
            logger.info(f"Knowledge item processed successfully: {knowledge_item_id}")
            
        except Exception as e:
            logger.error(f"Error processing knowledge item {knowledge_item_id}: {e}")
            knowledge_item.update_status(KnowledgeItemStatus.FAILED)
            await knowledge_item.save()

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
        
        knowledge_item.update_status(KnowledgeItemStatus.PARSED)
        await knowledge_item.save()

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
                knowledge_item.update_status(KnowledgeItemStatus.VECTORIZED)
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
                knowledge_item.update_status(KnowledgeItemStatus.COMPLETED)
                await knowledge_item.save()
                
                logger.info(f"Graph relations created for knowledge item: {knowledge_item.id}")
            else:
                raise Exception("Failed to create graph relations")
            
        except Exception as e:
            logger.error(f"Error creating graph relations for {knowledge_item.id}: {e}")
            raise

knowledge_processing_service = KnowledgeProcessingService()