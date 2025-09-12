# -*- coding: utf-8 -*-
# foxmask/tag/graphql.py
# GraphQL schema and resolvers for tag management

import strawberry
from typing import Optional, List
from .models import Tag, TagType as TagTypeModel
from .schemas import TagCreate, TagUpdate
from .services import tag_service
from foxmask.shared.dependencies import get_api_context, require_read, require_write, require_admin
from functools import wraps

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
            elif permission == "admin":
                api_key_info = await require_admin(request)
            else:
                api_key_info = await require_read(request)
            
            # Store API key info in context for later use
            info.context["api_key_info"] = api_key_info
            return await resolver(*args, **kwargs)
        return wrapper
    return decorator

@strawberry.type
class TagType:
    """GraphQL tag type"""
    id: strawberry.ID
    name: str
    type: str
    description: Optional[str]
    color: Optional[str]
    usage_count: int
    created_by: Optional[str]
    related_tags: List[str]
    is_active: bool
    created_at: str
    updated_at: str

@strawberry.type
class APIKeyInfo:
    """GraphQL API key information type"""
    api_key_id: str
    user_id: str
    permissions: List[str]
    client_ip: Optional[str]

@strawberry.type
class TagSearchResult:
    """GraphQL tag search result"""
    tags: List[TagType]
    total_count: int

@strawberry.input
class TagCreateInput:
    """GraphQL tag creation input"""
    name: str
    type: Optional[str] = "user"
    description: Optional[str] = None
    color: Optional[str] = "#6B7280"
    related_tags: Optional[List[str]] = strawberry.field(default_factory=list)

@strawberry.input
class TagUpdateInput:
    """GraphQL tag update input"""
    description: Optional[str] = None
    color: Optional[str] = None
    related_tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

def tag_to_gql(tag: Tag) -> TagType:
    """Convert Tag model to GraphQL type"""
    return TagType(
        id=strawberry.ID(str(tag.id)),
        name=tag.name,
        type=tag.type.value if hasattr(tag.type, 'value') else str(tag.type),
        description=tag.description,
        color=tag.color,
        usage_count=tag.usage_count,
        created_by=tag.created_by,
        related_tags=tag.related_tags,
        is_active=tag.is_active,
        created_at=tag.created_at.isoformat() if hasattr(tag.created_at, 'isoformat') else str(tag.created_at),
        updated_at=tag.updated_at.isoformat() if hasattr(tag.updated_at, 'isoformat') else str(tag.updated_at)
    )

@strawberry.type
class TagQuery:
    """GraphQL queries for tags"""
    
    @strawberry.field
    @api_key_required("read")
    async def tag(self, info, tag_id: strawberry.ID) -> TagType:
        """Get tag by ID"""
        api_key_info = info.context["api_key_info"]
        tag = await Tag.get(str(tag_id))
        
        if not tag:
            raise Exception("Tag not found")
        
        return tag_to_gql(tag)
    
    @strawberry.field
    @api_key_required("read")
    async def tag_by_name(self, info, name: str) -> TagType:
        """Get tag by name"""
        api_key_info = info.context["api_key_info"]
        tag = await Tag.find_one(Tag.name == name)
        
        if not tag:
            raise Exception("Tag not found")
        
        return tag_to_gql(tag)
    
    @strawberry.field
    @api_key_required("read")
    async def tags(
        self, 
        info, 
        skip: int = 0, 
        limit: int = 10,
        type: Optional[str] = None
    ) -> List[TagType]:
        """List tags with optional filtering"""
        api_key_info = info.context["api_key_info"]
        
        if type:
            tag_type = TagTypeModel(type)
            tags = await Tag.find(Tag.type == tag_type).skip(skip).limit(limit).to_list()
        else:
            tags = await Tag.find().skip(skip).limit(limit).to_list()
        
        return [tag_to_gql(tag) for tag in tags]
    
    @strawberry.field
    @api_key_required("read")
    async def search_tags(
        self, 
        info, 
        query: str,
        type: Optional[str] = None,
        skip: int = 0, 
        limit: int = 10
    ) -> TagSearchResult:
        """Search tags by name"""
        api_key_info = info.context["api_key_info"]
        
        tag_type = TagTypeModel(type) if type else None
        tags = await tag_service.search_tags(query, tag_type, skip, limit)
        
        # Build filter for total count
        filter_condition = {"name": {"$regex": query, "$options": "i"}}
        if tag_type:
            filter_condition["type"] = tag_type
        
        total_count = await Tag.find(filter_condition).count()
        
        return TagSearchResult(
            tags=[tag_to_gql(tag) for tag in tags],
            total_count=total_count
        )
    
    @strawberry.field
    @api_key_required("read")
    async def popular_tags(
        self, 
        info, 
        limit: int = 20
    ) -> List[TagType]:
        """Get most popular tags"""
        api_key_info = info.context["api_key_info"]
        tags = await tag_service.get_popular_tags(limit)
        return [tag_to_gql(tag) for tag in tags]
    
    @strawberry.field
    @api_key_required("read")
    async def my_tags(
        self, 
        info, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[TagType]:
        """Get tags created by current user"""
        api_key_info = info.context["api_key_info"]
        tags = await tag_service.get_user_tags(api_key_info["casdoor_user_id"], skip, limit)
        return [tag_to_gql(tag) for tag in tags]
    
    @strawberry.field
    @api_key_required("admin")
    async def system_tags(self, info) -> List[TagType]:
        """Get all system tags (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        tags = await tag_service.get_system_tags()
        return [tag_to_gql(tag) for tag in tags]
    
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
class TagMutation:
    """GraphQL mutations for tags"""
    
    @strawberry.mutation
    @api_key_required("write")
    async def create_tag(
        self, 
        info, 
        tag_data: TagCreateInput
    ) -> TagType:
        """Create a new tag"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to Pydantic model
        tag_dict = {k: v for k, v in tag_data.__dict__.items() if v is not None}
        tag_model = TagCreate(**tag_dict)
        
        tag = await tag_service.create_tag(tag_model, api_key_info["casdoor_user_id"])
        return tag_to_gql(tag)
    
    @strawberry.mutation
    @api_key_required("write")
    async def update_tag(
        self, 
        info, 
        tag_id: strawberry.ID,
        update_data: TagUpdateInput
    ) -> TagType:
        """Update tag"""
        api_key_info = info.context["api_key_info"]
        
        # First check if tag exists
        existing_tag = await Tag.get(str(tag_id))
        if not existing_tag:
            raise Exception("Tag not found")
        
        # Check permission - only creator or admin can update
        if (existing_tag.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to update this tag")
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = TagUpdate(**update_dict)
        
        tag = await tag_service.update_tag(str(tag_id), update_model, api_key_info["casdoor_user_id"])
        
        if not tag:
            raise Exception("Tag not found")
        
        return tag_to_gql(tag)
    
    @strawberry.mutation
    @api_key_required("write")
    async def delete_tag(
        self, 
        info, 
        tag_id: strawberry.ID
    ) -> bool:
        """Delete tag"""
        api_key_info = info.context["api_key_info"]
        
        # First check if tag exists
        existing_tag = await Tag.get(str(tag_id))
        if not existing_tag:
            raise Exception("Tag not found")
        
        # Check permission - only creator or admin can delete
        if (existing_tag.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to delete this tag")
        
        success = await tag_service.delete_tag(str(tag_id), api_key_info["casdoor_user_id"])
        
        if not success:
            raise Exception("Tag not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def increment_tag_usage(
        self, 
        info, 
        tag_id: strawberry.ID
    ) -> bool:
        """Increment tag usage count"""
        api_key_info = info.context["api_key_info"]
        success = await tag_service.increment_tag_usage(str(tag_id))
        
        if not success:
            raise Exception("Tag not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def decrement_tag_usage(
        self, 
        info, 
        tag_id: strawberry.ID
    ) -> bool:
        """Decrement tag usage count"""
        api_key_info = info.context["api_key_info"]
        success = await tag_service.decrement_tag_usage(str(tag_id))
        
        if not success:
            raise Exception("Tag not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def merge_tags(
        self, 
        info, 
        source_tag_id: strawberry.ID,
        target_tag_id: strawberry.ID
    ) -> bool:
        """Merge two tags (admin only)"""
        api_key_info = info.context["api_key_info"]
        
        # Only admin users can merge tags
        if "admin" not in api_key_info.get("permissions", []):
            raise Exception("Admin privileges required to merge tags")
        
        success = await tag_service.merge_tags(
            str(source_tag_id), str(target_tag_id), api_key_info["casdoor_user_id"]
        )
        
        if not success:
            raise Exception("Failed to merge tags")
        
        return True
    
    @strawberry.mutation
    @api_key_required("write")
    async def bulk_update_tags(
        self, 
        info, 
        tag_ids: List[strawberry.ID],
        update_data: TagUpdateInput
    ) -> List[TagType]:
        """Bulk update multiple tags"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = TagUpdate(**update_dict)
        
        updated_tags = []
        for tag_id in tag_ids:
            # Check permission for each tag
            existing_tag = await Tag.get(str(tag_id))
            if not existing_tag:
                continue
            
            if (existing_tag.created_by != api_key_info["casdoor_user_id"] and 
                "admin" not in api_key_info.get("permissions", [])):
                continue
            
            tag = await tag_service.update_tag(str(tag_id), update_model, api_key_info["casdoor_user_id"])
            if tag:
                updated_tags.append(tag_to_gql(tag))
        
        return updated_tags

# Schema definition
tag_schema = strawberry.Schema(
    query=TagQuery,
    mutation=TagMutation,
    types=[TagType, TagSearchResult, APIKeyInfo]
)