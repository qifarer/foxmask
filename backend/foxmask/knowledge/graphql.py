# -*- coding: utf-8 -*-
# foxmask/knowledge/graphql.py
# GraphQL schema and resolvers for knowledge items and knowledge bases

import strawberry
from strawberry.scalars import JSON as JSONScalar
from typing import Optional, List
from .models.knowledge_item import KnowledgeItem, KnowledgeItemStatus, KnowledgeItemType
from .models.knowledge_base import KnowledgeBase
from .services.knowledge_base import KnowledgeBaseService
from .services.knowledge_item import KnowledgeItemService
from foxmask.core.kafka import kafka_manager
from .schemas import KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeBaseCreate, KnowledgeBaseUpdate
from foxmask.shared.dependencies import get_api_context, require_read, require_write
from foxmask.core.config import settings
from functools import wraps
from enum import Enum

knowledge_base_service = KnowledgeBaseService()
knowledge_item_service = KnowledgeItemService()

# API Key context decorator for GraphQL
def api_key_required(permission: str = "read"):
    """Decorator to require API key authentication for GraphQL resolvers"""
    def decorator(resolver):
        @wraps(resolver)
        async def wrapper(*args, **kwargs):
            info = kwargs.get('info') or args[-1] if args else None
            if not info or not hasattr(info, 'context'):
                raise Exception("Authentication required")
            
            request = info.context.get("request")
            if not request:
                raise Exception("Request context not available")
            
            # Use appropriate permission dependency
            if permission == "read":
                api_key_info = await require_read(request)
            elif permission == "write":
                api_key_info = await require_write(request)
            else:
                api_key_info = await require_read(request)
            
            # Store API key info in context for later use
            info.context["api_key_info"] = api_key_info
            return await resolver(*args, **kwargs)
        return wrapper
    return decorator

@strawberry.type
class KnowledgeItemType:
    """GraphQL knowledge item type"""
    id: strawberry.ID
    title: str
    description: Optional[str]
    type: str
    status: str
    source_urls: List[str]
    file_ids: List[str]
    parsed_content: Optional[JSONScalar]
    vector_id: Optional[str]
    graph_id: Optional[str]
    tags: List[str]
    knowledge_base_ids: List[str]
    category: Optional[str]
    created_at: str
    updated_at: str
    created_by: str

@strawberry.type
class KnowledgeBaseType:
    """GraphQL knowledge base type"""
    id: strawberry.ID
    name: str
    description: Optional[str]
    is_public: bool
    tags: List[str]
    category: Optional[str]
    item_count: int
    created_at: str
    updated_at: str
    created_by: str

@strawberry.type
class APIKeyInfo:
    """GraphQL API key information type"""
    api_key_id: str
    user_id: str
    permissions: List[str]
    client_ip: Optional[str]

@strawberry.input
class KnowledgeItemCreateInput:
    """GraphQL knowledge item creation input"""
    title: str
    description: Optional[str] = None
    type: str
    source_urls: Optional[List[str]] = strawberry.field(default_factory=list)
    file_ids: Optional[List[str]] = strawberry.field(default_factory=list)
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    category: Optional[str] = None
    knowledge_base_ids: Optional[List[str]] = strawberry.field(default_factory=list)

@strawberry.input
class KnowledgeItemUpdateInput:
    """GraphQL knowledge item update input"""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None

@strawberry.input
class KnowledgeBaseCreateInput:
    """GraphQL knowledge base creation input"""
    name: str
    description: Optional[str] = None
    is_public: Optional[bool] = False
    tags: Optional[List[str]] = strawberry.field(default_factory=list)
    category: Optional[str] = None

@strawberry.input
class KnowledgeBaseUpdateInput:
    """GraphQL knowledge base update input"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None

@strawberry.input
class KnowledgeProcessingInput:
    """GraphQL knowledge processing input"""
    knowledge_item_id: strawberry.ID
    process_types: List[str]

def knowledge_item_to_gql(item: KnowledgeItem) -> KnowledgeItemType:
    """Convert KnowledgeItem model to GraphQL type"""
    return KnowledgeItemType(
        id=strawberry.ID(str(item.id)),
        title=item.title,
        description=item.description,
        type=item.type.value if hasattr(item.type, 'value') else str(item.type),
        status=item.status.value if hasattr(item.status, 'value') else str(item.status),
        source_urls=item.source_urls,
        file_ids=item.file_ids,
        parsed_content=item.parsed_content,
        vector_id=item.vector_id,
        graph_id=item.graph_id,
        tags=item.tags,
        knowledge_base_ids=item.knowledge_base_ids,
        category=item.category,
        created_at=item.created_at.isoformat() if hasattr(item.created_at, 'isoformat') else str(item.created_at),
        updated_at=item.updated_at.isoformat() if hasattr(item.updated_at, 'isoformat') else str(item.updated_at),
        created_by=item.created_by
    )

def knowledge_base_to_gql(kb: KnowledgeBase) -> KnowledgeBaseType:
    """Convert KnowledgeBase model to GraphQL type"""
    return KnowledgeBaseType(
        id=strawberry.ID(str(kb.id)),
        name=kb.name,
        description=kb.description,
        is_public=kb.is_public,
        tags=kb.tags,
        category=kb.category,
        item_count=kb.item_count,
        created_at=kb.created_at.isoformat() if hasattr(kb.created_at, 'isoformat') else str(kb.created_at),
        updated_at=kb.updated_at.isoformat() if hasattr(kb.updated_at, 'isoformat') else str(kb.updated_at),
        created_by=kb.created_by
    )

@strawberry.type
class KnowledgeQuery:
    """GraphQL queries for knowledge"""
    
    @strawberry.field
    @api_key_required("read")
    async def knowledge_item(self, info, item_id: strawberry.ID) -> KnowledgeItemType:
        """Get knowledge item by ID"""
        api_key_info = info.context["api_key_info"]
        item = await KnowledgeItem.get(str(item_id))
        
        if not item:
            raise Exception("Knowledge item not found")
        
        # Check permission
        if (item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to access this knowledge item")
        
        return knowledge_item_to_gql(item)
    
    @strawberry.field
    @api_key_required("read")
    async def knowledge_items(
        self, 
        info, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeItemType]:
        """Get user's knowledge items"""
        api_key_info = info.context["api_key_info"]
        items = await KnowledgeItem.find(
            KnowledgeItem.created_by == api_key_info["casdoor_user_id"]
        ).skip(skip).limit(limit).to_list()
        
        return [knowledge_item_to_gql(item) for item in items]
    
    @strawberry.field
    @api_key_required("read")
    async def knowledge_base(self, info, kb_id: strawberry.ID) -> KnowledgeBaseType:
        """Get knowledge base by ID"""
        api_key_info = info.context["api_key_info"]
        kb = await KnowledgeBase.get(str(kb_id))
        
        if not kb:
            raise Exception("Knowledge base not found")
        
        # Check permission
        if (kb.created_by != api_key_info["casdoor_user_id"] and 
            not kb.is_public and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to access this knowledge base")
        
        return knowledge_base_to_gql(kb)
    
    @strawberry.field
    @api_key_required("read")
    async def knowledge_bases(
        self, 
        info, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeBaseType]:
        """Get user's knowledge bases"""
        api_key_info = info.context["api_key_info"]
        bases = await KnowledgeBase.find(
            KnowledgeBase.created_by == api_key_info["casdoor_user_id"]
        ).skip(skip).limit(limit).to_list()
        
        return [knowledge_base_to_gql(kb) for kb in bases]
    
    @strawberry.field
    @api_key_required("read")
    async def public_knowledge_bases(
        self, 
        info, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeBaseType]:
        """Get public knowledge bases"""
        bases = await KnowledgeBase.find(
            KnowledgeBase.is_public == True
        ).skip(skip).limit(limit).to_list()
        
        return [knowledge_base_to_gql(kb) for kb in bases]
    
    @strawberry.field
    @api_key_required("read")
    async def knowledge_base_items(
        self, 
        info, 
        kb_id: strawberry.ID,
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeItemType]:
        """Get knowledge items in a knowledge base"""
        api_key_info = info.context["api_key_info"]
        kb = await KnowledgeBase.get(str(kb_id))
        
        if not kb:
            raise Exception("Knowledge base not found")
        
        # Check permission
        if (kb.created_by != api_key_info["casdoor_user_id"] and 
            not kb.is_public and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to access this knowledge base")
        
        items = await KnowledgeItem.find(
            KnowledgeItem.knowledge_base_ids == str(kb_id)
        ).skip(skip).limit(limit).to_list()
        
        return [knowledge_item_to_gql(item) for item in items]
    
    @strawberry.field
    @api_key_required("read")
    async def api_key_info(self, info) -> APIKeyInfo:
        """Get current API key information"""
        api_key_info = info.context["api_key_info"]
        return APIKeyInfo(
            api_key_id=api_key_info["api_key_id"],
            user_id=api_key_info["casdoor_user_id"],
            permissions=api_key_info.get("permissions", []),
            client_ip=api_key_info.get("client_ip")
        )

@strawberry.type
class KnowledgeMutation:
    """GraphQL mutations for knowledge"""
    
    @strawberry.mutation
    @api_key_required("write")
    async def create_knowledge_item(
        self, 
        info, 
        item_data: KnowledgeItemCreateInput
    ) -> KnowledgeItemType:
        """Create a new knowledge item"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to Pydantic model
        item_dict = {k: v for k, v in item_data.__dict__.items() if v is not None}
        item_model = KnowledgeItemCreate(**item_dict)
        
        item = await knowledge_item_service.create_knowledge_item(item_model, api_key_info["casdoor_user_id"])
        return knowledge_item_to_gql(item)
    
    @strawberry.mutation
    @api_key_required("write")
    async def update_knowledge_item(
        self, 
        info, 
        item_id: strawberry.ID,
        update_data: KnowledgeItemUpdateInput
    ) -> KnowledgeItemType:
        """Update knowledge item"""
        api_key_info = info.context["api_key_info"]
        
        # First check if item exists and user has permission
        existing_item = await KnowledgeItem.get(str(item_id))
        if not existing_item:
            raise Exception("Knowledge item not found")
        
        # Check permission
        if (existing_item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to update this knowledge item")
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = KnowledgeItemUpdate(**update_dict)
        
        item = await knowledge_item_service.update_knowledge_item(
            str(item_id), update_model, api_key_info["casdoor_user_id"]
        )
        
        if not item:
            raise Exception("Knowledge item not found")
        
        return knowledge_item_to_gql(item)
    
    @strawberry.mutation
    @api_key_required("write")
    async def delete_knowledge_item(
        self, 
        info, 
        item_id: strawberry.ID
    ) -> bool:
        """Delete knowledge item"""
        api_key_info = info.context["api_key_info"]
        
        # First check if item exists and user has permission
        existing_item = await KnowledgeItem.get(str(item_id))
        if not existing_item:
            raise Exception("Knowledge item not found")
        
        # Check permission
        if (existing_item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to delete this knowledge item")
        
        success = await knowledge_item_service.delete_knowledge_item(str(item_id), api_key_info["casdoor_user_id"])
        
        if not success:
            raise Exception("Knowledge item not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def create_knowledge_base(
        self, 
        info, 
        kb_data: KnowledgeBaseCreateInput
    ) -> KnowledgeBaseType:
        """Create a new knowledge base"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to Pydantic model
        kb_dict = {k: v for k, v in kb_data.__dict__.items() if v is not None}
        kb_model = KnowledgeBaseCreate(**kb_dict)
        
        kb = await knowledge_base_service.create_knowledge_base(kb_model, api_key_info["casdoor_user_id"])
        return knowledge_base_to_gql(kb)
    
    @strawberry.mutation
    @api_key_required("write")
    async def update_knowledge_base(
        self, 
        info, 
        kb_id: strawberry.ID,
        update_data: KnowledgeBaseUpdateInput
    ) -> KnowledgeBaseType:
        """Update knowledge base"""
        api_key_info = info.context["api_key_info"]
        
        # First check if base exists and user has permission
        existing_kb = await KnowledgeBase.get(str(kb_id))
        if not existing_kb:
            raise Exception("Knowledge base not found")
        
        # Check permission
        if (existing_kb.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to update this knowledge base")
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = KnowledgeBaseUpdate(**update_dict)
        
        kb = await knowledge_base_service.update_knowledge_base(
            str(kb_id), update_model, api_key_info["casdoor_user_id"]
        )
        
        if not kb:
            raise Exception("Knowledge base not found")
        
        return knowledge_base_to_gql(kb)
    
    @strawberry.mutation
    @api_key_required("write")
    async def delete_knowledge_base(
        self, 
        info, 
        kb_id: strawberry.ID
    ) -> bool:
        """Delete knowledge base"""
        api_key_info = info.context["api_key_info"]
        
        # First check if base exists and user has permission
        existing_kb = await KnowledgeBase.get(str(kb_id))
        if not existing_kb:
            raise Exception("Knowledge base not found")
        
        # Check permission
        if (existing_kb.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to delete this knowledge base")
        
        success = await knowledge_base_service.delete_knowledge_base(str(kb_id), api_key_info["casdoor_user_id"])
        
        if not success:
            raise Exception("Knowledge base not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def add_to_knowledge_base(
        self, 
        info, 
        item_id: strawberry.ID,
        kb_id: strawberry.ID
    ) -> bool:
        """Add knowledge item to knowledge base"""
        api_key_info = info.context["api_key_info"]
        
        # Check if both item and base exist and user has permission
        item = await KnowledgeItem.get(str(item_id))
        if not item:
            raise Exception("Knowledge item not found")
        
        kb = await KnowledgeBase.get(str(kb_id))
        if not kb:
            raise Exception("Knowledge base not found")
        
        # Check permission for both item and base
        if (item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to modify this knowledge item")
        
        if (kb.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to modify this knowledge base")
        
        success = await knowledge_item_service.add_to_knowledge_base(
            str(item_id), str(kb_id), api_key_info["casdoor_user_id"]
        )
        
        if not success:
            raise Exception("Failed to add item to knowledge base")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def remove_from_knowledge_base(
        self, 
        info, 
        item_id: strawberry.ID,
        kb_id: strawberry.ID
    ) -> bool:
        """Remove knowledge item from knowledge base"""
        api_key_info = info.context["api_key_info"]
        
        # Check if both item and base exist and user has permission
        item = await KnowledgeItem.get(str(item_id))
        if not item:
            raise Exception("Knowledge item not found")
        
        kb = await KnowledgeBase.get(str(kb_id))
        if not kb:
            raise Exception("Knowledge base not found")
        
        # Check permission for both item and base
        if (item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to modify this knowledge item")
        
        if (kb.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to modify this knowledge base")
        
        success = await knowledge_item_service.remove_from_knowledge_base(
            str(item_id), str(kb_id), api_key_info["casdoor_user_id"]
        )
        
        if not success:
            raise Exception("Failed to remove item from knowledge base")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def process_knowledge_item(
        self, 
        info, 
        processing_data: KnowledgeProcessingInput
    ) -> bool:
        """Trigger processing for a knowledge item"""
        api_key_info = info.context["api_key_info"]
        item = await KnowledgeItem.get(str(processing_data.knowledge_item_id))
        
        if not item:
            raise Exception("Knowledge item not found")
        
        # Check permission
        if (item.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to process this knowledge item")
        
        # Send processing message with API key context
        message = {
            "knowledge_item_id": str(processing_data.knowledge_item_id),
            "process_types": processing_data.process_types,
            "api_key_id": api_key_info["api_key_id"],
            "user_id": api_key_info["casdoor_user_id"]
        }
        
        await kafka_manager.send_message(settings.KAFKA_KNOWLEDGE_TOPIC, message)
        return True

# Schema definition
knowledge_schema = strawberry.Schema(
    query=KnowledgeQuery,
    mutation=KnowledgeMutation,
    types=[KnowledgeItemType, KnowledgeBaseType, APIKeyInfo]
)