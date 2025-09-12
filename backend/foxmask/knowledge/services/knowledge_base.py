from typing import Optional, List
from fastapi import HTTPException, status
from foxmask.core.logger import logger

from ..models.knowledge_base import KnowledgeBase
from ..models.knowledge_item import KnowledgeItem
from ..schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate

class KnowledgeBaseService:
    async def create_knowledge_base(self, kb_data: KnowledgeBaseCreate, user_id: str) -> KnowledgeBase:
        """Create a new knowledge base"""
        try:
            knowledge_base = KnowledgeBase(
                **kb_data.model_dump(),
                created_by=user_id
            )
            
            await knowledge_base.insert()
            logger.info(f"Knowledge base created: {knowledge_base.name} by user {user_id}")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Error creating knowledge base: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create knowledge base: {e}"
            )

    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get knowledge base by ID"""
        return await KnowledgeBase.get(kb_id)

    async def update_knowledge_base(
        self, 
        kb_id: str, 
        update_data: KnowledgeBaseUpdate, 
        user_id: str
    ) -> Optional[KnowledgeBase]:
        """Update knowledge base"""
        knowledge_base = await self.get_knowledge_base(kb_id)
        if not knowledge_base:
            return None
        
        # Check permission
        if knowledge_base.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this knowledge base"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(knowledge_base, field, value)
        
        knowledge_base.update_timestamp()
        await knowledge_base.save()
        
        logger.info(f"Knowledge base updated: {kb_id} by user {user_id}")
        return knowledge_base

    async def delete_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """Delete knowledge base"""
        knowledge_base = await self.get_knowledge_base(kb_id)
        if not knowledge_base:
            return False
        
        # Check permission
        if knowledge_base.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this knowledge base"
            )
        
        await knowledge_base.delete()
        logger.info(f"Knowledge base deleted: {kb_id} by user {user_id}")
        return True

    async def list_user_knowledge_bases(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeBase]:
        """List knowledge bases created by a user"""
        return await KnowledgeBase.find(
            KnowledgeBase.created_by == user_id
        ).skip(skip).limit(limit).to_list()

    async def list_public_knowledge_bases(
        self, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeBase]:
        """List public knowledge bases"""
        return await KnowledgeBase.find(
            KnowledgeBase.is_public == True
        ).skip(skip).limit(limit).to_list()

    async def get_knowledge_base_items(
        self, 
        kb_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeItem]:
        """Get knowledge items in a knowledge base"""
        return await KnowledgeItem.find(
            KnowledgeItem.knowledge_base_ids == kb_id
        ).skip(skip).limit(limit).to_list()

knowledge_base_service = KnowledgeBaseService()