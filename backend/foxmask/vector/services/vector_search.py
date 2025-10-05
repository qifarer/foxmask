# -*- coding: utf-8 -*-
# Vector search service for indexing and searching knowledge items using Weaviate

from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np
from foxmask.core.logger import logger
from foxmask.utils.weaviate_manager import weaviate_client_manager, WeaviateClass

class VectorSearchService:
    async def index_knowledge_item(self, knowledge_item: Dict[str, Any]) -> Optional[str]:
        """Index a knowledge item in Weaviate"""
        try:
            properties = {
                "knowledgeItemId": knowledge_item["id"],
                "title": knowledge_item.get("title", ""),
                "description": knowledge_item.get("description", ""),
                "content": knowledge_item.get("parsed_content", {}).get("content", ""),
                "type": knowledge_item.get("type", ""),
                "tags": knowledge_item.get("tags", []),
                "category": knowledge_item.get("category", ""),
                "status": knowledge_item.get("status", ""),
                "createdBy": knowledge_item.get("created_by", ""),
                "createdAt": knowledge_item.get("created_at", datetime.utcnow()).isoformat(),
                "updatedAt": knowledge_item.get("updated_at", datetime.utcnow()).isoformat()
            }
            
            # Remove empty values
            properties = {k: v for k, v in properties.items() if v not in [None, "", []]}
            
            object_id = await weaviate_client_manager.create_object(
                class_name=WeaviateClass.KNOWLEDGE_ITEM,
                properties=properties
            )
            
            return object_id
            
        except Exception as e:
            logger.error(f"Error indexing knowledge item: {e}")
            return None

    async def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        certainty: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on knowledge items"""
        try:
            results = await weaviate_client_manager.semantic_search(
                class_name=WeaviateClass.KNOWLEDGE_ITEM,
                query=query,
                properties=["title", "description", "content", "tags", "category"],
                limit=limit,
                certainty=certainty,
                filters=filters
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search (vector + keyword)"""
        try:
            results = await weaviate_client_manager.hybrid_search(
                class_name=WeaviateClass.KNOWLEDGE_ITEM,
                query=query,
                properties=["title", "description", "content", "tags", "category"],
                limit=limit,
                alpha=alpha,
                filters=filters
            )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            return []

    def _format_search_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Format Weaviate search results"""
        formatted_results = []
        
        for result in results:
            formatted = {
                "id": result.get("knowledgeItemId"),
                "title": result.get("title"),
                "description": result.get("description"),
                "type": result.get("type"),
                "category": result.get("category"),
                "certainty": result.get("_additional", {}).get("certainty", 0),
                "distance": result.get("_additional", {}).get("distance", 0),
                "vector": result.get("_additional", {}).get("vector"),
                "tags": result.get("tags", [])
            }
            
            # Add additional metadata if available
            additional = result.get("_additional", {})
            if "id" in additional:
                formatted["weaviate_id"] = additional["id"]
            
            formatted_results.append(formatted)
        
        return formatted_results

    async def find_similar_items(
        self,
        item_id: str,
        limit: int = 10,
        certainty: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar items using vector similarity"""
        try:
            # First get the vector of the target item
            target_item = await weaviate_client_manager.get_object_by_id(item_id)
            if not target_item or "_additional" not in target_item:
                return []
            
            vector = target_item["_additional"].get("vector")
            if not vector:
                return []
            
            # Find similar items using vector search
            similar_items = await weaviate_client_manager.get_similar_objects(
                class_name=WeaviateClass.KNOWLEDGE_ITEM,
                vector=vector,
                properties=["title", "description", "type", "category", "tags"],
                limit=limit,
                certainty=certainty
            )
            
            return self._format_search_results(similar_items)
            
        except Exception as e:
            logger.error(f"Error finding similar items: {e}")
            return []

    async def batch_index_items(self, knowledge_items: List[Dict[str, Any]]) -> List[str]:
        """Batch index multiple knowledge items"""
        try:
            objects = []
            
            for item in knowledge_items:
                properties = {
                    "knowledgeItemId": item["id"],
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "content": item.get("parsed_content", {}).get("content", ""),
                    "type": item.get("type", ""),
                    "tags": item.get("tags", []),
                    "category": item.get("category", ""),
                    "status": item.get("status", ""),
                    "createdBy": item.get("created_by", ""),
                    "createdAt": item.get("created_at", datetime.utcnow()).isoformat(),
                    "updatedAt": item.get("updated_at", datetime.utcnow()).isoformat()
                }
                
                # Remove empty values
                properties = {k: v for k, v in properties.items() if v not in [None, "", []]}
                objects.append(properties)
            
            object_ids = await weaviate_client_manager.batch_upload_objects(
                class_name=WeaviateClass.KNOWLEDGE_ITEM,
                objects=objects
            )
            
            return object_ids
            
        except Exception as e:
            logger.error(f"Error batch indexing items: {e}")
            return []

    async def get_index_statistics(self) -> Optional[Dict[str, Any]]:
        """Get statistics about the vector index"""
        try:
            stats = await weaviate_client_manager.get_class_statistics(WeaviateClass.KNOWLEDGE_ITEM)
            return stats
            
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return None

    async def delete_from_index(self, item_id: str) -> bool:
        """Delete a knowledge item from the vector index"""
        try:
            # First find the Weaviate object ID
            query = f"""
            {{
                Get {{
                    {WeaviateClass.KNOWLEDGE_ITEM} (
                        where: {{
                            path: ["knowledgeItemId"],
                            operator: Equal,
                            valueString: "{item_id}"
                        }}
                    ) {{
                        _additional {{
                            id
                        }}
                    }}
                }}
            }}
            """
            
            result = weaviate_client_manager.client.query.raw(query)
            items = result.get("data", {}).get("Get", {}).get(WeaviateClass.KNOWLEDGE_ITEM, [])
            
            if items and "_additional" in items[0]:
                weaviate_id = items[0]["_additional"]["id"]
                return await weaviate_client_manager.delete_object(weaviate_id)
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting from index: {e}")
            return False

# Global vector search service instance
vector_search_service = VectorSearchService()