# schema_manager.py
from weaviate.classes.config import Property, DataType, ReferenceProperty, Configure
from weaviate.classes.config import Multi2VecField, VectorDistances  # 需要导入 Multi2VecField 和 VectorDistances
from typing import Dict, List, Any, Optional

from foxmask.utils.weaviate_manager import weaviate_client_manager, WeaviateClass
from foxmask.core.logger import logger

class SchemaManager:
    """Manager for Weaviate schema operations"""
    
    def __init__(self):
        self.client_manager = weaviate_client_manager
    
    def initialize_schema(self) -> bool:
        """Initialize Weaviate schema with optimized configuration using Weaviate v4 API"""
        try:
            with self.client_manager.get_connection() as client:
                existing_classes = client.collections.list_all()
                # self.delete_class(WeaviateClass.KNOWLEDGE_ITEM_CONTENT)
                # self.delete_class(WeaviateClass.KNOWLEDGE_ITEM)
                   
                # Create KnowledgeItem class if not exists
                if WeaviateClass.KNOWLEDGE_ITEM not in existing_classes:
                    self._create_knowledge_item_class(client)
                    logger.info(f"Created Weaviate class: {WeaviateClass.KNOWLEDGE_ITEM}")
                
                # Create KnowledgeItemContent class if not exists
                if WeaviateClass.KNOWLEDGE_ITEM_CONTENT not in existing_classes:
                    self._create_knowledge_item_content_class(client)
                    logger.info(f"Created Weaviate class: {WeaviateClass.KNOWLEDGE_ITEM_CONTENT}")
                
                logger.info("Weaviate schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing Weaviate schema: {e}")
            return False
    
    def _create_knowledge_item_class(self, client):
        """Create KnowledgeItem class using Weaviate v4 API with multi2vec_bind vectorizer"""
        client.collections.create(
            name=WeaviateClass.KNOWLEDGE_ITEM,
            description="Knowledge items with metadata and relationships to content",
            vectorizer_config=[
                Configure.NamedVectors.multi2vec_bind(
                    name="item_title_vector",
                    text_fields=[
                        Multi2VecField(name="title", weight=0.5),
                        Multi2VecField(name="description", weight=0.3),
                        Multi2VecField(name="tags", weight=0.2),
                    ],
                )
            ],
            generative_config=Configure.Generative.ollama(
                api_endpoint="http://host.docker.internal:11434",
                model="deepseek-r1:7b"
            ),
            properties=[
                Property(
                    name="itemId",
                    data_type=DataType.TEXT,
                    description="业务ID (字符串)",
                    index_filterable=True,
                    index_searchable=False
                ),
                Property(
                    name="sourceId",
                    data_type=DataType.TEXT,
                    description="源ID (字符串)",
                    index_filterable=True,
                    index_searchable=False
                ),
                Property(
                    name="itemType",
                    data_type=DataType.TEXT,
                    description="Type of knowledge item",
                    index_filterable=True,
                    index_searchable=True
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Title of the knowledge item",
                    index_filterable=True,
                    index_searchable=True
                ),
                Property(
                    name="description",
                    data_type=DataType.TEXT,
                    description="Description of the knowledge item",
                    index_searchable=True
                ),
                Property(
                    name="metadata",
                    data_type=DataType.OBJECT,
                    description="元数据",
                    nested_properties=[
                        Property(name="type", data_type=DataType.TEXT),
                        Property(name="name", data_type=DataType.TEXT),
                        Property(name="path", data_type=DataType.TEXT),
                        Property(name="url", data_type=DataType.TEXT),
                        Property(name="keyword", data_type=DataType.TEXT),
                        Property(name="size", data_type=DataType.INT),
                        Property(name="updateAt", data_type=DataType.DATE)
                    ]
                ),
                Property(
                    name="note",
                    data_type=DataType.TEXT,
                    description="note of the knowledge item",
                    index_searchable=True
                ),
                Property(
                    name="tags",
                    data_type=DataType.TEXT_ARRAY,
                    description="Tags associated with the knowledge item",
                    index_filterable=True,
                    index_searchable=True
                ),
                Property(
                    name="status",
                    data_type=DataType.TEXT,
                    description="Processing status",
                    index_filterable=True
                ),
                Property(
                    name="visibility",
                    data_type=DataType.TEXT,
                    description="Visibility level",
                    index_filterable=True
                ),
                Property(
                    name="tenantId",
                    data_type=DataType.TEXT,
                    description="Tenant ID",
                    index_filterable=True
                ),
                Property(
                    name="createdBy",
                    data_type=DataType.TEXT,
                    description="Creator user ID",
                    index_filterable=True
                ),
                Property(
                    name="allowedUsers",
                    data_type=DataType.TEXT_ARRAY,
                    description="Allowed user IDs",
                    index_filterable=True
                ),
                Property(
                    name="allowedRoles",
                    data_type=DataType.TEXT_ARRAY,
                    description="Allowed role IDs",
                    index_filterable=True
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="Creation timestamp",
                    index_filterable=True
                ),
                Property(
                    name="updatedAt",
                    data_type=DataType.DATE,
                    description="Last update timestamp",
                    index_filterable=True
                ),
            ]
        )

    def _create_knowledge_item_content_class(self, client):
        """Create KnowledgeItemContent class using Weaviate v4 API"""
        client.collections.create(
            name=WeaviateClass.KNOWLEDGE_ITEM_CONTENT,
            description="Content blocks of knowledge items with vector embeddings",
            vectorizer_config=[
                Configure.NamedVectors.multi2vec_bind(
                    name="content_vector",
                    text_fields=[
                        Multi2VecField(name="srcTitle", weight=0.2),
                        Multi2VecField(name="srcSummary", weight=0.1),
                        Multi2VecField(name="cntSummary", weight=0.2),
                        Multi2VecField(name="cntText", weight=0.3),
                        Multi2VecField(name="cntBlob", weight=0.2),
                    ],
                )
            ],
            generative_config=Configure.Generative.ollama(
                api_endpoint="http://host.docker.internal:11434",
                model="deepseek-r1:7b"
            ),
            properties=[
                Property(
                    name="contentId",
                    data_type=DataType.TEXT,
                    description="业务ID (字符串)",
                    index_filterable=True
                ),
                Property(
                    name="itemId",
                    data_type=DataType.TEXT,
                    description="关联的业务ID",
                    index_filterable=True
                ),
                Property(
                    name="tenantId",
                    data_type=DataType.TEXT,
                    description="Tenant ID",
                    index_filterable=True
                ),
                Property(
                    name="srcId",
                    data_type=DataType.TEXT,
                    description="源ID",
                    index_filterable=True,
                ),
                Property(
                    name="srcTitle",
                    data_type=DataType.TEXT,
                    description="源标题",
                    index_filterable=True,
                    index_searchable=True
                ),
                Property(
                    name="srcSummary",
                    data_type=DataType.TEXT,
                    description="源摘要",
                    index_searchable=True
                ),
                Property(
                    name="srcKeyword",
                    data_type=DataType.TEXT,
                    description="源关键词",
                    index_searchable=True
                ),
              
                Property(
                    name="cntType",
                    data_type=DataType.TEXT,
                    description="内容类型",
                    index_filterable=True
                ),
                Property(
                    name="cntText",
                    data_type=DataType.TEXT,
                    description="内容Text",
                    index_searchable=True
                ),
                Property(
                    name="cntBlob",
                    data_type=DataType.BLOB,
                    description="内容Blob",
                ),
                Property(
                    name="cntSummary",
                    data_type=DataType.TEXT,
                    description="内容摘要",
                    index_searchable=True
                ),
                Property(
                    name="cntTags",
                    data_type=DataType.TEXT_ARRAY,
                    description="内容标签",
                    index_filterable=True,
                    index_searchable=True
                ),
                Property(
                    name="cntMeta",
                    data_type=DataType.OBJECT,
                    description="内容元数据",
                    nested_properties=[
                        Property(name="type", data_type=DataType.TEXT),
                        Property(name="seqno", data_type=DataType.INT),
                        Property(name="total", data_type=DataType.INT),
                    ]
                ),
                Property(
                    name="version",
                    data_type=DataType.INT,
                    description="版本号",
                    index_filterable=True
                ),
                Property(
                    name="isLatest",
                    data_type=DataType.BOOL,
                    description="是否是最新版本",
                    index_filterable=True
                ),
                Property(
                    name="createdBy",
                    data_type=DataType.TEXT,
                    description="创建者",
                    index_filterable=True
                ),
                Property(
                    name="createdAt",
                    data_type=DataType.DATE,
                    description="创建时间",
                    index_filterable=True
                ),
                Property(
                    name="updatedAt",
                    data_type=DataType.DATE,
                    description="更新时间",
                    index_filterable=True
                )
            ],
            references=[
                ReferenceProperty(
                    name="belongsToItem",
                    target_collection=WeaviateClass.KNOWLEDGE_ITEM,
                    description="Reference to the parent knowledge item"
                )
            ]
        )
    
    # 其余方法保持不变...
    def update_schema(self, class_name: str) -> bool:
        """Update existing class schema - limited capabilities in Weaviate v4"""
        try:
            with self.client_manager.get_connection() as client:
                if class_name not in client.collections.list_all():
                    logger.error(f"Class {class_name} does not exist")
                    return False
                
                logger.warning(f"Schema updates may require class recreation for {class_name} in Weaviate v4")
                return True
                
        except Exception as e:
            logger.error(f"Error updating schema for {class_name}: {e}")
            return False
    
    def get_class_stats(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a Weaviate class"""
        try:
            with self.client_manager.get_connection() as client:
                if class_name not in client.collections.list_all():
                    return None
                
                collection = client.collections.get(class_name)
                config = collection.config.get()
                
                # Get object count
                count_result = collection.aggregate.over_all(total_count=True)
                
                return {
                    "class_name": class_name,
                    "object_count": count_result.total_count,
                    "vectorizer": config.vectorizer,
                    "vector_index_type": config.vector_index_type,
                    "properties": [prop.name for prop in config.properties],
                    "sharding_config": config.sharding_config
                }
                
        except Exception as e:
            logger.error(f"Error getting stats for {class_name}: {e}")
            return None
    
    def delete_class(self, class_name: str) -> bool:
        """Delete a Weaviate class (use with caution)"""
        try:
            with self.client_manager.get_connection() as client:
                if class_name in client.collections.list_all():
                    client.collections.delete(class_name)
                    logger.warning(f"Deleted Weaviate class: {class_name}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting class {class_name}: {e}")
            return False

# Global schema manager instance
weaviate_schema_manager = SchemaManager()