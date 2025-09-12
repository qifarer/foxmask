from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from .models import KnowledgeItem, KnowledgeBase, SourceType, KnowledgeType, ItemStatus, AccessLevel
from .schemas import (
    KnowledgeItemSchema, KnowledgeBaseSchema, KnowledgeContentSchema,
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeBaseCreate, KnowledgeBaseUpdate,
    KnowledgeContentCreate, ResponseSchema, PaginatedResponse,
    KnowledgeItemQuery, KnowledgeBaseQuery
)
from .services import knowledge_item_service, knowledge_base_service
from foxmask.core.casdoor_auth import get_current_user
from bson import ObjectId
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# 知识条目路由
@router.get("/items", response_model=PaginatedResponse)
async def list_items(
    query: KnowledgeItemQuery = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    获取知识条目列表（支持过滤和分页）
    """
    try:
        # 构建过滤条件
        filters = {}
        if query.title:
            filters["title"] = query.title
        if query.source_type:
            filters["source_type"] = query.source_type
        if query.knowledge_type:
            filters["knowledge_type"] = query.knowledge_type
        if query.status:
            filters["status"] = query.status
        if query.created_by:
            filters["created_by"] = query.created_by
        if query.tenant_id:
            filters["tenant_id"] = query.tenant_id
        
        items = await knowledge_item_service.list_items(
            skip=(query.page - 1) * query.size,
            limit=query.size,
            filters=filters
        )
        
        # 获取总数（这里需要实现计数方法）
        total = len(items)  # 简化处理，实际应该从数据库获取总数
        
        return PaginatedResponse(
            total=total,
            page=query.page,
            size=query.size,
            items=items
        )
        
    except Exception as e:
        logger.error(f"Failed to list items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve items"
        )

@router.get("/items/{item_id}", response_model=KnowledgeItemSchema)
async def get_item(
    item_id: str = Path(..., description="知识条目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取特定知识条目的详细信息
    """
    try:
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        # 检查访问权限
        if not _check_item_access(item, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve item"
        )

@router.post("/items", response_model=KnowledgeItemSchema, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: KnowledgeItemCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建新的知识条目
    """
    try:
        user_id = current_user.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        # 转换知识库ID格式
        knowledge_base_ids = []
        if item_data.knowledge_bases:
            knowledge_base_ids = [ObjectId(kb_id) for kb_id in item_data.knowledge_bases if ObjectId.is_valid(kb_id)]
        
        item = await knowledge_item_service.create_item(
            title=item_data.title,
            description=item_data.description,
            source_type=item_data.source_type,
            knowledge_type=item_data.knowledge_type,
            sources=item_data.sources,
            source_urls=item_data.source_urls or [],
            metadata=item_data.metadata or {},
            user_id=user_id,
            updated_by=user_id,
            tenant_id=item_data.tenant_id,
            tags=item_data.tags,
            knowledge_bases=knowledge_base_ids,
            category=item_data.category,
            subcategory=item_data.subcategory
        )
        
        return item
        
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )

@router.put("/items/{item_id}", response_model=KnowledgeItemSchema)
async def update_item(
    item_id: str = Path(..., description="知识条目ID"),
    item_data: KnowledgeItemUpdate = None,
    current_user: dict = Depends(get_current_user)
):
    """
    更新知识条目信息
    """
    try:
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        user_id = current_user.get("sub", "")
        
        # 检查权限
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        if not _check_item_access(item, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # 转换知识库ID格式
        knowledge_base_ids = None
        if item_data.knowledge_bases is not None:
            knowledge_base_ids = [ObjectId(kb_id) for kb_id in item_data.knowledge_bases if ObjectId.is_valid(kb_id)]
        
        updated_item = await knowledge_item_service.update_item(
            ObjectId(item_id),
            title=item_data.title,
            description=item_data.description,
            source_type=item_data.source_type,
            knowledge_type=item_data.knowledge_type,
            sources=item_data.sources,
            source_urls=item_data.source_urls,
            metadata=item_data.metadata,
            updated_by=user_id,
            tags=item_data.tags,
            knowledge_bases=knowledge_base_ids,
            category=item_data.category,
            subcategory=item_data.subcategory,
            access_level=item_data.access_level
        )
        
        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        return updated_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item"
        )

@router.delete("/items/{item_id}", response_model=ResponseSchema)
async def delete_item(
    item_id: str = Path(..., description="知识条目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    删除知识条目（软删除）
    """
    try:
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        # 检查权限
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        if not _check_item_access(item, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = await knowledge_item_service.delete_item(ObjectId(item_id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Item deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )

@router.patch("/items/{item_id}/status", response_model=KnowledgeItemSchema)
async def update_item_status(
    item_id: str = Path(..., description="知识条目ID"),
    status: ItemStatus = Query(..., description="新的状态"),
    error_message: Optional[str] = Query(None, description="错误信息"),
    current_user: dict = Depends(get_current_user)
):
    """
    更新知识条目状态
    """
    try:
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        success = await knowledge_item_service.update_item_status(
            ObjectId(item_id), status, error_message
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Item not found"
            )
        
        # 返回更新后的条目
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        return item
        
    except Exception as e:
        logger.error(f"Failed to update item status {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item status"
        )

# 知识库路由
@router.get("/bases", response_model=PaginatedResponse)
async def list_bases(
    query: KnowledgeBaseQuery = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    获取知识库列表（支持过滤和分页）
    """
    try:
        # 构建过滤条件
        filters = {}
        if query.name:
            filters["name"] = query.name
        if query.category:
            filters["category"] = query.category
        if query.access_level:
            filters["access_level"] = query.access_level
        if query.created_by:
            filters["created_by"] = query.created_by
        if query.tenant_id:
            filters["tenant_id"] = query.tenant_id
        if query.is_active is not None:
            filters["is_active"] = query.is_active
        
        bases = await knowledge_base_service.list_bases(
            skip=(query.page - 1) * query.size,
            limit=query.size,
            filters=filters
        )
        
        # 获取总数
        total = len(bases)  # 简化处理
        
        return PaginatedResponse(
            total=total,
            page=query.page,
            size=query.size,
            items=bases
        )
        
    except Exception as e:
        logger.error(f"Failed to list bases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bases"
        )

@router.get("/bases/{base_id}", response_model=KnowledgeBaseSchema)
async def get_base(
    base_id: str = Path(..., description="知识库ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取特定知识库的详细信息
    """
    try:
        if not ObjectId.is_valid(base_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        base = await knowledge_base_service.get_base(ObjectId(base_id))
        if not base:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base not found"
            )
        
        # 检查访问权限
        if not _check_base_access(base, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return base
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get base {base_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve base"
        )

@router.post("/bases", response_model=KnowledgeBaseSchema, status_code=status.HTTP_201_CREATED)
async def create_base(
    base_data: KnowledgeBaseCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建新的知识库
    """
    try:
        user_id = current_user.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        base = await knowledge_base_service.create_base(
            name=base_data.name,
            description=base_data.description,
            user_id=user_id,
            tenant_id=base_data.tenant_id,
            access_level=base_data.access_level,
            tags=base_data.tags,
            category=base_data.category,
            collaborators=base_data.collaborators or []
        )
        
        return base
        
    except Exception as e:
        logger.error(f"Failed to create base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create base"
        )

@router.put("/bases/{base_id}", response_model=KnowledgeBaseSchema)
async def update_base(
    base_id: str = Path(..., description="知识库ID"),
    base_data: KnowledgeBaseUpdate = None,
    current_user: dict = Depends(get_current_user)
):
    """
    更新知识库信息
    """
    try:
        if not ObjectId.is_valid(base_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        user_id = current_user.get("sub", "")
        
        # 检查权限
        base = await knowledge_base_service.get_base(ObjectId(base_id))
        if not base:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base not found"
            )
        
        if not _check_base_access(base, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        updated_base = await knowledge_base_service.update_base(
            ObjectId(base_id),
            name=base_data.name,
            description=base_data.description,
            updated_by=user_id,
            tags=base_data.tags,
            category=base_data.category,
            access_level=base_data.access_level,
            collaborators=base_data.collaborators,
            is_active=base_data.is_active
        )
        
        if not updated_base:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base not found"
            )
        
        return updated_base
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update base {base_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update base"
        )

@router.delete("/bases/{base_id}", response_model=ResponseSchema)
async def delete_base(
    base_id: str = Path(..., description="知识库ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    删除知识库（软删除）
    """
    try:
        if not ObjectId.is_valid(base_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        # 检查权限
        base = await knowledge_base_service.get_base(ObjectId(base_id))
        if not base:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base not found"
            )
        
        if not _check_base_access(base, current_user, require_owner=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        success = await knowledge_base_service.delete_base(ObjectId(base_id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Base deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete base {base_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete base"
        )

@router.post("/bases/{base_id}/items/{item_id}", response_model=ResponseSchema)
async def add_item_to_base(
    base_id: str = Path(..., description="知识库ID"),
    item_id: str = Path(..., description="知识条目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    将知识条目添加到知识库
    """
    try:
        if not ObjectId.is_valid(base_id) or not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        success = await knowledge_base_service.add_item_to_base(
            ObjectId(base_id), ObjectId(item_id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base or item not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Item added to base successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to add item to base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to base"
        )

@router.delete("/bases/{base_id}/items/{item_id}", response_model=ResponseSchema)
async def remove_item_from_base(
    base_id: str = Path(..., description="知识库ID"),
    item_id: str = Path(..., description="知识条目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    从知识库移除知识条目
    """
    try:
        if not ObjectId.is_valid(base_id) or not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid ID format"
            )
        
        success = await knowledge_base_service.remove_item_from_base(
            ObjectId(base_id), ObjectId(item_id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Base or item not found"
            )
        
        return ResponseSchema(
            success=True,
            message="Item removed from base successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to remove item from base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item from base"
        )

# 辅助函数
def _check_item_access(item: KnowledgeItem, user: dict, require_owner: bool = False) -> bool:
    """
    检查用户对知识条目的访问权限
    """
    user_id = user.get("sub")
    user_roles = user.get("roles", [])
    
    # 管理员有完全访问权限
    if "admin" in user_roles:
        return True
    
    # 检查访问级别
    if item.access_level == AccessLevel.PUBLIC:
        return True
    elif item.access_level == AccessLevel.TENANT:
        # 检查是否在同一租户
        user_tenant = user.get("tenant_id")
        return user_tenant == item.tenant_id
    elif item.access_level == AccessLevel.USER:
        # 检查是否是创建者
        return user_id == item.created_by
    elif item.access_level == AccessLevel.PRIVATE:
        # 需要特定权限
        return require_owner and user_id == item.created_by
    
    return False

def _check_base_access(base: KnowledgeBase, user: dict, require_owner: bool = False) -> bool:
    """
    检查用户对知识库的访问权限
    """
    user_id = user.get("sub")
    user_roles = user.get("roles", [])
    
    # 管理员有完全访问权限
    if "admin" in user_roles:
        return True
    
    # 检查访问级别
    if base.access_level == AccessLevel.PUBLIC:
        return True
    elif base.access_level == AccessLevel.TENANT:
        # 检查是否在同一租户
        user_tenant = user.get("tenant_id")
        return user_tenant == base.tenant_id
    elif base.access_level == AccessLevel.USER:
        # 检查是否是创建者或协作者
        return user_id == base.created_by or user_id in base.collaborators
    elif base.access_level == AccessLevel.PRIVATE:
        # 需要特定权限
        return require_owner and user_id == base.created_by
    
    return False