import weaviate
from weaviate import Client
from weaviate.exceptions import WeaviateQueryError, ObjectAlreadyExistsException
from typing import Optional, Dict, List, Any, Union
import json
import asyncio
from datetime import datetime
from enum import Enum
import numpy as np

from foxmask.core.config import settings
from foxmask.core.logger import logger

class WeaviateClass(str, Enum):
    """Weaviate class names"""
    KNOWLEDGE_ITEM = "KnowledgeItem"
    DOCUMENT = "Document"
    USER = "User"
    TAG = "Tag"

class WeaviateDistanceMetric(str, Enum):
    """Weaviate distance metrics"""
    COSINE = "cosine"
    EUCLIDEAN = "l2-squared"
    DOT = "dot"
    MANHATTAN = "manhattan"

class WeaviateClient:
    def __init__(self):
        self.client: Optional[Client] = None
        self.connected = False
        self.batch_size = 100
        self.batch_objects = []

    async def connect(self):
        """Connect to Weaviate"""
        try:
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=settings.WEAVIATE_URL,
                auth_credentials=weaviate.auth.AuthApiKey(settings.WEAVIATE_API_KEY) if hasattr(settings, 'WEAVIATE_API_KEY') else None,
                timeout_config=(5, 15)  # (connect timeout, read timeout)
            )
            
            # Test connection
            self.client.collections.list_all()
            self.connected = True
            logger.info("Connected to Weaviate successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            self.connected = False
            raise

    async def ensure_schema_exists(self):
        """Ensure Weaviate schema exists with all required classes"""
        if not self.connected:
            await self.connect()
        
        try:
            # Check if classes exist and create them if not
            existing_classes = self.client.collections.list_all()
            
            classes_to_create = [
                self._get_knowledge_item_class(),
                self._get_document_class(),
                self._get_user_class(),
                self._get_tag_class()
            ]
            
            for class_obj in classes_to_create:
                if class_obj["class"] not in existing_classes:
                    self.client.collections.create_from_dict(class_obj)
                    logger.info(f"Created Weaviate class: {class_obj['class']}")
            
            logger.info("Weaviate schema ensured successfully")
            
        except Exception as e:
            logger.error(f"Error ensuring Weaviate schema: {e}")
            raise

    def _get_knowledge_item_class(self) -> Dict[str, Any]:
        """Get KnowledgeItem class definition"""
        return {
            "class": WeaviateClass.KNOWLEDGE_ITEM,
            "description": "Knowledge items with vector embeddings",
            "vectorizer": "text2vec-transformers",
            "moduleConfig": {
                "text2vec-transformers": {
                    "poolingStrategy": "masked_mean",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "knowledgeItemId",
                    "dataType": ["string"],
                    "description": "ID of the knowledge item in the main database",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "skip": True
                        }
                    }
                },
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Title of the knowledge item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "vectorizePropertyName": True
                        }
                    }
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Description of the knowledge item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "vectorizePropertyName": True
                        }
                    }
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Main content of the knowledge item",
                    "moduleConfig": {
                        "text2vec-transformers": {
                            "vectorizePropertyName": True
                        }
                    }
                },
                {
                    "name": "type",
                    "dataType": ["string"],
                    "description": "Type of knowledge item (file, webpage, etc.)"
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"],
                    "description": "Tags associated with the knowledge item"
                },
                {
                    "name": "category",
                    "dataType": ["string"],
                    "description": "Category of the knowledge item"
                },
                {
                    "name": "status",
                    "dataType": ["string"],
                    "description": "Processing status of the knowledge item"
                },
                {
                    "name": "createdBy",
                    "dataType": ["string"],
                    "description": "User ID who created the knowledge item"
                },
                {
                    "name": "createdAt",
                    "dataType": ["date"],
                    "description": "Creation timestamp"
                },
                {
                    "name": "updatedAt",
                    "dataType": ["date"],
                    "description": "Last update timestamp"
                }
            ],
            "vectorIndexConfig": {
                "distance": WeaviateDistanceMetric.COSINE,
                "efConstruction": 128,
                "maxConnections": 64,
                "ef": -1,
                "dynamicEfFactor": 8,
                "dynamicEfMin": 100,
                "dynamicEfMax": 500
            }
        }

    def _get_document_class(self) -> Dict[str, Any]:
        """Get Document class definition"""
        return {
            "class": WeaviateClass.DOCUMENT,
            "description": "Document files with vector embeddings",
            "vectorizer": "text2vec-transformers",
            "properties": [
                {
                    "name": "documentId",
                    "dataType": ["string"],
                    "description": "ID of the document in the main database"
                },
                {
                    "name": "filename",
                    "dataType": ["string"],
                    "description": "Original filename"
                },
                {
                    "name": "contentType",
                    "dataType": ["string"],
                    "description": "File content type"
                },
                {
                    "name": "extractedText",
                    "dataType": ["text"],
                    "description": "Extracted text content from the document"
                },
                {
                    "name": "fileSize",
                    "dataType": ["int"],
                    "description": "File size in bytes"
                }
            ]
        }

    def _get_user_class(self) -> Dict[str, Any]:
        """Get User class definition"""
        return {
            "class": WeaviateClass.USER,
            "description": "System users",
            "vectorizer": "none",  # Users typically don't need vectorization
            "properties": [
                {
                    "name": "userId",
                    "dataType": ["string"],
                    "description": "ID of the user in the main database"
                },
                {
                    "name": "username",
                    "dataType": ["string"],
                    "description": "User's username"
                },
                {
                    "name": "email",
                    "dataType": ["string"],
                    "description": "User's email address"
                },
                {
                    "name": "displayName",
                    "dataType": ["string"],
                    "description": "User's display name"
                }
            ]
        }

    def _get_tag_class(self) -> Dict[str, Any]:
        """Get Tag class definition"""
        return {
            "class": WeaviateClass.TAG,
            "description": "Content tags",
            "vectorizer": "text2vec-transformers",
            "properties": [
                {
                    "name": "tagId",
                    "dataType": ["string"],
                    "description": "ID of the tag in the main database"
                },
                {
                    "name": "name",
                    "dataType": ["string"],
                    "description": "Tag name"
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Tag description"
                },
                {
                    "name": "usageCount",
                    "dataType": ["int"],
                    "description": "Number of times this tag is used"
                }
            ]
        }

    async def create_object(
        self, 
        class_name: str, 
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None,
        tenant: Optional[str] = None
    ) -> Optional[str]:
        """Create object in Weaviate"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            result = collection.data.insert(
                properties=properties,
                vector=vector,
                tenant=tenant
            )
            return result.uuid
        except ObjectAlreadyExistsException:
            logger.warning(f"Object already exists in class {class_name}")
            return None
        except Exception as e:
            logger.error(f"Error creating Weaviate object: {e}")
            return None

    async def get_object(self, object_id: str, class_name: str) -> Optional[Dict]:
        """Get object from Weaviate by ID"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            result = collection.query.fetch_object_by_id(object_id)
            return result
        except Exception as e:
            logger.error(f"Error getting Weaviate object: {e}")
            return None

    async def update_object(
        self, 
        object_id: str, 
        class_name: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> bool:
        """Update object in Weaviate"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            collection.data.update(
                uuid=object_id,
                properties=properties,
                vector=vector
            )
            return True
        except Exception as e:
            logger.error(f"Error updating Weaviate object: {e}")
            return False

    async def delete_object(self, object_id: str, class_name: str) -> bool:
        """Delete object from Weaviate"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            collection.data.delete_by_id(object_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting Weaviate object: {e}")
            return False

    async def semantic_search(
        self,
        class_name: str,
        query: str,
        properties: List[str] = None,
        limit: int = 10,
        certainty: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        autocut: Optional[int] = None
    ) -> List[Dict]:
        """Perform semantic search with filters"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            
            near_text = {
                "concepts": [query],
                "certainty": certainty
            }
            
            query_builder = collection.query.near_text(
                query=query,
                certainty=certainty,
                limit=limit,
                return_metadata=weaviate.classes.query.MetadataQuery(certainty=True)
            )
            
            if properties:
                query_builder = query_builder.return_properties(properties)
            
            if filters:
                where_clause = self._build_where_clause(filters)
                query_builder = query_builder.with_where(where_clause)
            
            if autocut:
                query_builder = query_builder.with_autocut(autocut)
            
            result = query_builder.do()
            
            return [obj.properties for obj in result.objects]
            
        except WeaviateQueryError as e:
            logger.error(f"Weaviate query error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build Weaviate where clause from filters"""
        operands = []
        
        for field, value in filters.items():
            if isinstance(value, dict):
                # Complex filter with operator
                operator = value.get('operator', 'Equal')
                filter_value = value.get('value')
                
                if operator == 'Equal':
                    operands.append({
                        "path": [field],
                        "operator": "Equal",
                        "valueString": filter_value
                    })
                elif operator == 'ContainsAny':
                    operands.append({
                        "path": [field],
                        "operator": "ContainsAny",
                        "valueStringArray": filter_value
                    })
                elif operator == 'GreaterThan':
                    operands.append({
                        "path": [field],
                        "operator": "GreaterThan",
                        "valueNumber": filter_value
                    })
            else:
                # Simple equality filter
                operands.append({
                    "path": [field],
                    "operator": "Equal",
                    "valueString": value
                })
        
        return {"operands": operands, "operator": "And"}

    async def hybrid_search(
        self,
        class_name: str,
        query: str,
        properties: List[str] = None,
        limit: int = 10,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """Perform hybrid search (vector + keyword)"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            
            query_builder = collection.query.hybrid(
                query=query,
                alpha=alpha,
                limit=limit,
                return_metadata=weaviate.classes.query.MetadataQuery(score=True)
            )
            
            if properties:
                query_builder = query_builder.return_properties(properties)
            
            if filters:
                where_clause = self._build_where_clause(filters)
                query_builder = query_builder.with_where(where_clause)
            
            result = query_builder.do()
            
            return [obj.properties for obj in result.objects]
            
        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            return []

    async def batch_upload_objects(
        self, 
        class_name: str, 
        objects: List[Dict[str, Any]],
        vectors: Optional[List[List[float]]] = None
    ) -> List[str]:
        """Batch upload objects to Weaviate"""
        if not self.connected:
            await self.connect()
        
        object_ids = []
        
        try:
            collection = self.client.collections.get(class_name)
            
            with collection.batch.dynamic() as batch:
                for i, obj in enumerate(objects):
                    vector = vectors[i] if vectors and i < len(vectors) else None
                    
                    batch.add_object(
                        properties=obj,
                        vector=vector
                    )
            
            logger.info(f"Batch uploaded {len(objects)} objects to {class_name}")
            return object_ids
            
        except Exception as e:
            logger.error(f"Error batch uploading to Weaviate: {e}")
            return []

    async def get_similar_objects(
        self,
        class_name: str,
        vector: List[float],
        properties: List[str] = None,
        limit: int = 10,
        certainty: float = 0.7
    ) -> List[Dict]:
        """Find similar objects using vector similarity"""
        if not self.connected:
            await self.connect()
        
        try:
            collection = self.client.collections.get(class_name)
            
            query_builder = collection.query.near_vector(
                near_vector=vector,
                certainty=certainty,
                limit=limit,
                return_metadata=weaviate.classes.query.MetadataQuery(certainty=True)
            )
            
            if properties:
                query_builder = query_builder.return_properties(properties)
            
            result = query_builder.do()
            
            return [obj.properties for obj in result.objects]
            
        except Exception as e:
            logger.error(f"Error finding similar objects: {e}")
            return []

    async def get_class_statistics(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a Weaviate class"""
        if not self.connected:
            await self.connect()
        
        try:
            # Get class schema
            collection = self.client.collections.get(class_name)
            class_info = collection.config.get()
            
            # Get object count
            count_result = collection.aggregate.over_all(total_count=True)
            count = count_result.total_count
            
            return {
                "class_name": class_name,
                "object_count": count,
                "properties": [prop.name for prop in class_info.properties],
                "vectorizer": class_info.vectorizer
            }
            
        except Exception as e:
            logger.error(f"Error getting class statistics: {e}")
            return None

    async def close(self):
        """Close Weaviate connection"""
        if self.client:
            self.client.close()
        self.connected = False
        logger.info("Weaviate connection closed")

# Global Weaviate client instance
weaviate_client = WeaviateClient()