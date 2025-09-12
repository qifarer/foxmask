from typing import Optional, List, Dict
from fastapi import HTTPException, status
from foxmask.core.logger import logger
from .models import Tag, TagType
from .schemas import TagCreate, TagUpdate

class TagService:
    async def create_tag(self, tag_data: TagCreate, user_id: str) -> Tag:
        """Create a new tag"""
        try:
            # Check if tag already exists
            existing_tag = await Tag.find_one(Tag.name == tag_data.name)
            if existing_tag:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Tag '{tag_data.name}' already exists"
                )
            
            tag = Tag(
                **tag_data.model_dump(),
                created_by=user_id
            )
            
            await tag.insert()
            logger.info(f"Tag created: {tag.name} by user {user_id}")
            return tag
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create tag: {e}"
            )

    async def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID"""
        return await Tag.get(tag_id)

    async def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name"""
        return await Tag.find_one(Tag.name == name)

    async def update_tag(
        self, 
        tag_id: str, 
        update_data: TagUpdate, 
        user_id: str
    ) -> Optional[Tag]:
        """Update tag"""
        tag = await self.get_tag(tag_id)
        if not tag:
            return None
        
        # Check permission (users can only update their own tags)
        if tag.created_by != user_id and tag.type != TagType.SYSTEM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this tag"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(tag, field, value)
        
        tag.update_timestamp()
        await tag.save()
        
        logger.info(f"Tag updated: {tag_id} by user {user_id}")
        return tag

    async def delete_tag(self, tag_id: str, user_id: str) -> bool:
        """Delete tag"""
        tag = await self.get_tag(tag_id)
        if not tag:
            return False
        
        # Check permission (users can only delete their own tags, system tags cannot be deleted)
        if tag.type == TagType.SYSTEM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System tags cannot be deleted"
            )
        
        if tag.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this tag"
            )
        
        await tag.delete()
        logger.info(f"Tag deleted: {tag_id} by user {user_id}")
        return True

    async def increment_tag_usage(self, tag_id: str) -> bool:
        """Increment tag usage count"""
        tag = await self.get_tag(tag_id)
        if not tag:
            return False
        
        tag.increment_usage()
        await tag.save()
        return True

    async def decrement_tag_usage(self, tag_id: str) -> bool:
        """Decrement tag usage count"""
        tag = await self.get_tag(tag_id)
        if not tag:
            return False
        
        tag.decrement_usage()
        await tag.save()
        return True

    async def search_tags(
        self, 
        query: str, 
        tag_type: Optional[TagType] = None,
        skip: int = 0, 
        limit: int = 10
    ) -> List[Tag]:
        """Search tags by name"""
        search_filter = {"name": {"$regex": query, "$options": "i"}}
        if tag_type:
            search_filter["type"] = tag_type
        
        return await Tag.find(search_filter).skip(skip).limit(limit).to_list()

    async def get_popular_tags(
        self, 
        limit: int = 20
    ) -> List[Tag]:
        """Get most popular tags by usage count"""
        return await Tag.find(
            Tag.is_active == True
        ).sort(-Tag.usage_count).limit(limit).to_list()

    async def get_user_tags(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[Tag]:
        """Get tags created by a user"""
        return await Tag.find(
            Tag.created_by == user_id
        ).skip(skip).limit(limit).to_list()

    async def get_system_tags(self) -> List[Tag]:
        """Get all system tags"""
        return await Tag.find(
            Tag.type == TagType.SYSTEM
        ).to_list()

    async def batch_update_tag_usage(self, tag_usage: Dict[str, int]):
        """Batch update tag usage counts"""
        for tag_id, count in tag_usage.items():
            tag = await self.get_tag(tag_id)
            if tag:
                tag.usage_count = count
                tag.update_timestamp()
                await tag.save()

tag_service = TagService()