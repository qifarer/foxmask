from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from .models import Tag, TaggedObject, TagTypeEnum, TagCollection
from .schemas import (
    TagSchema, TaggedObjectSchema, TagUsageStatsSchema, TagCollectionSchema,
    TagCreate, TagUpdate, TaggedObjectCreate, TagCollectionCreate,
    ResponseSchema, PaginatedResponse, TagQuery, TagSearchQuery
)
from .services import tag_service
from foxmask.core.casdoor_auth import get_current_user
from bson import ObjectId
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tags", tags=["tags"])

# 标签路由
@router.get("/", response_model=PaginatedResponse)
async def list_tags(
    query: TagQuery = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    获取标签列表（支持过滤和分页）
    """
    try:
        # 构建过滤条件
        filters = {}
        if query.tag_type:
            filters["tag_type"] = query.tag_type
        if query.tenant_id:
            filters["tenant_id"] = query.tenant_id
        if query.is_public is not None:
            filters["is_public"] = query.is_public
        if query.created_by:
            filters["created_by"] = query.created_by
        if query.parent_id:
            if ObjectId.is_valid(query.parent_id):
                filters["parent_id"] = ObjectId(query.parent_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid parent ID format"
                )
        if query.status:
            filters["status"] = query.status
        
        tags = await tag_service.list_tags(
            skip=(query.page - 1) * query.size,
            limit=query.size,
            filters=filters
        )
        
        # 获取总数（这里需要实现计数方法）
        total = len(tags)  # 简化处理
        
        return PaginatedResponse(
            total=total,
            page=query.page,
            size=query.size,
            items=tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tags"
        )

@router.get("/search", response_model=PaginatedResponse)
async def search_tags(
    search_query: TagSearchQuery = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    搜索标签
    """
    try:
        tags = await tag_service.search_tags(
            query=search_query.query,
            skip=(search_query.page - 1) * search_query.size,
            limit=search_query.size,
            tenant_id=search_query.tenant_id
        )
        
        total = len(tags)  # 简化处理
        
        return PaginatedResponse(
            total=total,
            page=search_query.page,
            size=search_query.size,
            items=tags
        )
        
    except Exception as e:
        logger.error(f"Failed to search tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search tags"
        )

@router.get("/popular", response_model=List[TagSchema])
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    tenant_id: Optional[str] = Query(None, description="租户ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取热门标签
    """
    try:
        tags = await tag_service.get_popular_tags(limit, tenant_id)
        return tags
        
    except Exception as e:
        logger.error(f"Failed to get popular tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular tags"
        )

@router.get("/{tag_id}", response_model=TagSchema)
async def get_tag(
    tag_id: str = Path(..., description="标签ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取特定标签的详细信息
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        tag = await tag_service.get_tag(ObjectId(tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag not found"
            )
        
        # 检查访问权限
        if not _check_tag_access(tag, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return tag
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tag {tag_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tag"
        )

@router.post("/", response_model=TagSchema, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建新的标签
    """
    try:
        user_id = current_user.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # 检查标签名是否已存在（在同一个租户内）
        existing_tag = await tag_service.get_tag_by_name(
            tag_data.name, tag_data.tenant_id
        )
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag with this name already exists"
            )
        
        # 转换父标签ID
        parent_object_id = None
        if tag_data.parent_id and ObjectId.is_valid(tag_data.parent_id):
            parent_object_id = ObjectId(tag_data.parent_id)
        
        tag = await tag_service.create_tag(
            name=tag_data.name,
            user_id=user_id,
            tag_type=tag_data.tag_type,
            description=tag_data.description,
            color=tag_data.color,
            icon=tag_data.icon,
            parent_id=parent_object_id,
            is_public=tag_data.is_public,
            tenant_id=tag_data.tenant_id,
            metadata=tag_data.metadata
        )
        
        return tag
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tag"
        )

@router.put("/{tag_id}", response_model=TagSchema)
async def update_tag(
    tag_id: str = Path(..., description="标签ID"),
    tag_data: TagUpdate=None,
    current_user: dict = Depends(get_current_user)
):
    """
    更新标签信息
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        user_id = current_user.get("sub", "")
        
        # 检查权限
        tag = await tag_service.get_tag(ObjectId(tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag not found"
            )
        
        if not _check_tag_access(tag, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # 如果更新名称，检查是否冲突
        if tag_data.name and tag_data.name != tag.name:
            existing_tag = await tag_service.get_tag_by_name(
                tag_data.name, tag.tenant_id
            )
            if existing_tag and existing_tag.id != ObjectId(tag_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Tag with this name already exists"
                )
        
        # 转换父标签ID
        parent_object_id = None
        if tag_data.parent_id and ObjectId.is_valid(tag_data.parent_id):
            parent_object_id = ObjectId(tag_data.parent_id)
        
        updated_tag = await tag_service.update_tag(
            ObjectId(tag_id),
            user_id=user_id,
            name=tag_data.name,
            description=tag_data.description,
            color=tag_data.color,
            icon=tag_data.icon,
            parent_id=parent_object_id,
            is_public=tag_data.is_public,
            metadata=tag_data.metadata,
            status=tag_data.status
        )
        
        if not updated_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag not found"
            )
        
        return updated_tag
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tag {tag_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tag"
        )

@router.delete("/{tag_id}", response_model=ResponseSchema)
async def delete_tag(
    tag_id: str = Path(..., description="标签ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    删除标签（软删除）
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        # 检查权限
        tag = await tag_service.get_tag(ObjectId(tag_id))
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag not found"
            )
        
        if not _check_tag_access(tag, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = await tag_service.delete_tag(ObjectId(tag_id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Tag deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete tag {tag_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag"
        )

@router.post("/{tag_id}/objects", response_model=ResponseSchema)
async def tag_object(
    tag_id: str = Path(..., description="标签ID"),
    tag_data: TaggedObjectCreate = None,
    current_user: dict = Depends(get_current_user)
):
    """
    标记对象
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        if not tag_data or not ObjectId.is_valid(tag_data.object_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object ID format"
            )
        
        # 验证对象类型
        valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
        if tag_data.object_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object type"
            )
        
        tagged_object = await tag_service.tag_object(
            ObjectId(tag_id),
            tag_data.object_type,
            ObjectId(tag_data.object_id),
            current_user.get("sub", ""),
            tag_data.weight,
            tag_data.context,
            tag_data.source
        )
        
        if not tagged_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found or object already tagged"
            )
        
        return ResponseSchema(
            success=True,
            message="Object tagged successfully",
            data={"tagged_object_id": str(tagged_object.id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to tag object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to tag object"
        )

@router.delete("/{tag_id}/objects/{object_type}/{object_id}", response_model=ResponseSchema)
async def untag_object(
    tag_id: str = Path(..., description="标签ID"),
    object_type: str = Path(..., description="对象类型"),
    object_id: str = Path(..., description="对象ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    取消标记对象
    """
    try:
        if not ObjectId.is_valid(tag_id) or not ObjectId.is_valid(object_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        # 验证对象类型
        valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
        if object_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object type"
            )
        
        success = await tag_service.untag_object(
            ObjectId(tag_id),
            object_type,
            ObjectId(object_id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tag relationship not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Object untagged successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to untag object: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to untag object"
        )

@router.get("/objects/{object_type}/{object_id}", response_model=List[TagSchema])
async def get_object_tags(
    object_type: str = Path(..., description="对象类型"),
    object_id: str = Path(..., description="对象ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取对象的标签
    """
    try:
        if not ObjectId.is_valid(object_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object ID format"
            )
        
        # 验证对象类型
        valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
        if object_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object type"
            )
        
        tags = await tag_service.get_object_tags(object_type, ObjectId(object_id))
        return tags
        
    except Exception as e:
        logger.error(f"Failed to get object tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve object tags"
        )

@router.get("/{tag_id}/objects", response_model=List[TaggedObjectSchema])
async def get_tagged_objects(
    tag_id: str = Path(..., description="标签ID"),
    object_type: Optional[str] = Query(None, description="对象类型"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    获取标记的对象
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        # 验证对象类型（如果提供）
        if object_type:
            valid_types = {'knowledge_item', 'knowledge_base', 'file', 'user', 'document'}
            if object_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid object type"
                )
        
        objects = await tag_service.get_tagged_objects(
            ObjectId(tag_id), object_type, skip, limit
        )
        return objects
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tagged objects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tagged objects"
        )

@router.get("/{tag_id}/related", response_model=List[TagSchema])
async def get_related_tags(
    tag_id: str = Path(..., description="标签ID"),
    limit: int = Query(10, ge=1, le=20),
    current_user: dict = Depends(get_current_user)
):
    """
    获取相关标签
    """
    try:
        if not ObjectId.is_valid(tag_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tag ID format"
            )
        
        tags = await tag_service.get_related_tags(ObjectId(tag_id), limit)
        return tags
        
    except Exception as e:
        logger.error(f"Failed to get related tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve related tags"
        )

# 辅助函数
def _check_tag_access(tag: Tag, user: dict, require_owner: bool = False) -> bool:
    """
    检查用户对标签的访问权限
    """
    user_id = user.get("sub")
    user_roles = user.get("roles", [])
    
    # 管理员有完全访问权限
    if "admin" in user_roles:
        return True
    
    # 检查是否公开
    if tag.is_public:
        return True
    
    # 检查是否是所有者
    if user_id == tag.owner_id or user_id == tag.created_by:
        return True
    
    # 检查是否在同一租户
    user_tenant = user.get("tenant_id")
    if user_tenant and user_tenant == tag.tenant_id:
        return not require_owner
    
    return False