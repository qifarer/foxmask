from typing import Optional, List
from fastapi import HTTPException, status
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings

from ..models.knowledge_item import KnowledgeItem, KnowledgeItemStatus, KnowledgeItemType
from ..schemas import KnowledgeItemCreate, KnowledgeItemUpdate

class KnowledgeItemService:
    async def create_knowledge_item(self, item_data: KnowledgeItemCreate, user_id: str) -> KnowledgeItem:
        """Create a new knowledge item"""
        try:
            knowledge_item = KnowledgeItem(
                **item_data.model_dump(exclude={"knowledge_base_ids"}),
                created_by=user_id
            )
            
            # Add to knowledge bases if specified
            for kb_id in item_data.knowledge_base_ids:
                knowledge_item.add_to_knowledge_base(kb_id)
            
            await knowledge_item.insert()
            logger.info(f"Knowledge item created: {knowledge_item.title} by user {user_id}")
            
            # Send Kafka message for processing
            await self._send_processing_message(knowledge_item)
            
            return knowledge_item
            
        except Exception as e:
            logger.error(f"Error creating knowledge item: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create knowledge item: {e}"
            )

    async def get_knowledge_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get knowledge item by ID"""
        return await KnowledgeItem.get(item_id)

    async def update_knowledge_item(
        self, 
        item_id: str, 
        update_data: KnowledgeItemUpdate, 
        user_id: str
    ) -> Optional[KnowledgeItem]:
        """Update knowledge item"""
        knowledge_item = await self.get_knowledge_item(item_id)
        if not knowledge_item:
            return None
        
        # Check permission
        if knowledge_item.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this knowledge item"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(knowledge_item, field, value)
        
        knowledge_item.update_status(KnowledgeItemStatus.CREATED)
        await knowledge_item.save()
        
        # Send Kafka message for reprocessing
        await self._send_processing_message(knowledge_item)
        
        logger.info(f"Knowledge item updated: {item_id} by user {user_id}")
        return knowledge_item

    async def delete_knowledge_item(self, item_id: str, user_id: str) -> bool:
        """Delete knowledge item"""
        knowledge_item = await self.get_knowledge_item(item_id)
        if not knowledge_item:
            return False
        
        # Check permission
        if knowledge_item.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this knowledge item"
            )
        
        await knowledge_item.delete()
        logger.info(f"Knowledge item deleted: {item_id} by user {user_id}")
        return True

    async def list_user_knowledge_items(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[KnowledgeItem]:
        """List knowledge items created by a user"""
        return await KnowledgeItem.find(
            KnowledgeItem.created_by == user_id
        ).skip(skip).limit(limit).to_list()

    async def add_to_knowledge_base(self, item_id: str, kb_id: str, user_id: str) -> bool:
        """Add knowledge item to knowledge base"""
        knowledge_item = await self.get_knowledge_item(item_id)
        if not knowledge_item:
            return False
        
        # Check permission
        if knowledge_item.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this knowledge item"
            )
        
        knowledge_item.add_to_knowledge_base(kb_id)
        await knowledge_item.save()
        
        logger.info(f"Knowledge item {item_id} added to knowledge base {kb_id}")
        return True

    async def remove_from_knowledge_base(self, item_id: str, kb_id: str, user_id: str) -> bool:
        """Remove knowledge item from knowledge base"""
        knowledge_item = await self.get_knowledge_item(item_id)
        if not knowledge_item:
            return False
        
        # Check permission
        if knowledge_item.created_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this knowledge item"
            )
        
        knowledge_item.remove_from_knowledge_base(kb_id)
        await knowledge_item.save()
        
        logger.info(f"Knowledge item {item_id} removed from knowledge base {kb_id}")
        return True

    async def _send_processing_message(self, knowledge_item: KnowledgeItem):
        """Send Kafka message for knowledge item processing"""
        message = {
            "knowledge_item_id": str(knowledge_item.id),
            "type": knowledge_item.type,
            "process_types": ["parse", "vectorize", "graph"]  # Default processing types
        }
        
        try:
            await kafka_manager.send_message(settings.KAFKA_KNOWLEDGE_TOPIC, message)
            logger.info(f"Processing message sent for knowledge item: {knowledge_item.id}")
        except Exception as e:
            logger.error(f"Failed to send processing message: {e}")

knowledge_item_service = KnowledgeItemService()