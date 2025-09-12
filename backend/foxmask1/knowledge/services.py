from .models import KnowledgeItem, KnowledgeBase, ItemStatus, SourceType, KnowledgeType, AccessLevel
from foxmask.core.kafka import kafka_producer
from foxmask.core.minio import minio_client
from foxmask.tag.services import tag_service
from foxmask.tag.utils import tag_utils
from typing import List, Optional, Dict, Any
from bson import ObjectId
from uuid import UUID
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class KnowledgeItemService:
    def __init__(self):
        self.minio_client = minio_client
    
    async def create_item(self, title: str, description: Optional[str], source_type: SourceType,
                         knowledge_type: KnowledgeType, sources: List[str], metadata: Dict[str, Any],
                         user_id: str, updated_by: str, tenant_id: Optional[str] = None,
                         tags: Optional[List[str]] = None, knowledge_bases: Optional[List[ObjectId]] = None,
                         category: Optional[str] = None, subcategory: Optional[str] = None,
                         source_urls: Optional[List[str]] = None) -> KnowledgeItem:
        """创建知识条目"""
        try:
            item = KnowledgeItem(
                title=title,
                description=description,
                source_type=source_type,
                knowledge_type=knowledge_type,
                sources=sources,
                source_urls=source_urls or [],
                metadata=metadata,
                category=category,
                subcategory=subcategory,
                tenant_id=tenant_id,
                created_by=user_id,
                updated_by=updated_by,
                status=ItemStatus.CREATED,
                knowledge_bases=knowledge_bases or []
            )
            
            await item.insert()
            
            # 批量添加标签
            if tags:
                await self._update_item_tags(item, tags, user_id)
            
            # 发送Kafka消息开始处理流程
            await kafka_producer.send_message("knowledge-item-created", {
                "item_id": str(item.id),
                "source_type": source_type.value,
                "knowledge_type": knowledge_type.value,
                "sources": sources
            })
            
            logger.info(f"Created knowledge item {item.id} by user {user_id}")
            return item
            
        except Exception as e:
            logger.error(f"Failed to create knowledge item: {e}")
            raise
    
    async def update_item(self, item_id: ObjectId, title: str, description: Optional[str], 
                         source_type: SourceType, knowledge_type: KnowledgeType, 
                         sources: List[str], metadata: Dict[str, Any], updated_by: str,
                         tags: Optional[List[str]] = None, knowledge_bases: Optional[List[ObjectId]] = None,
                         category: Optional[str] = None, subcategory: Optional[str] = None,
                         source_urls: Optional[List[str]] = None) -> Optional[KnowledgeItem]:
        """更新知识条目"""
        try:
            item = await KnowledgeItem.get(item_id)
            if not item:
                logger.warning(f"Knowledge item {item_id} not found")
                return None
            
            # 更新基本信息
            item.title = title
            item.description = description
            item.source_type = source_type
            item.knowledge_type = knowledge_type
            item.sources = sources
            item.source_urls = source_urls or []
            item.metadata = metadata
            item.category = category
            item.subcategory = subcategory
            item.updated_by = updated_by
            item.knowledge_bases = knowledge_bases or []
            item.update_timestamp()
            
            # 更新标签
            if tags is not None:
                await self._update_item_tags(item, tags, updated_by)
            
            await item.save()
            
            # 如果源数据有变化，重新处理
            sources_changed = sources != item.sources
            if sources_changed:
                await kafka_producer.send_message("knowledge-item-updated", {
                    "item_id": str(item.id),
                    "source_type": source_type.value,
                    "knowledge_type": knowledge_type.value,
                    "sources": sources
                })
            
            logger.info(f"Updated knowledge item {item_id} by user {updated_by}")
            return item
            
        except Exception as e:
            logger.error(f"Failed to update knowledge item {item_id}: {e}")
            raise
    
    async def _update_item_tags(self, item: KnowledgeItem, tags: List[str], user_id: str):
        """更新条目标签"""
        try:
            # 获取当前标签
            current_tags = await tag_service.get_object_tags("knowledge_item", str(item.id))
            current_tag_names = [tag.name for tag in current_tags]
            
            # 需要添加的标签
            tags_to_add = [tag for tag in tags if tag not in current_tag_names]
            # 需要移除的标签
            tags_to_remove = [tag for tag in current_tag_names if tag not in tags]
            
            # 批量添加新标签
            if tags_to_add:
                tagged_ids = await tag_utils.batch_tag_objects(
                    tags_to_add, "knowledge_item", str(item.id), user_id
                )
                # 更新标签引用（使用Link，不需要手动转换）
                # 这里需要根据实际的tag_service实现调整
            
            # 批量移除标签
            if tags_to_remove:
                await tag_utils.batch_untag_objects(
                    tags_to_remove, "knowledge_item", str(item.id)
                )
            
            # 重新加载标签引用
            await item.fetch_all_links()
            
        except Exception as e:
            logger.error(f"Failed to update tags for item {item.id}: {e}")
            raise
    
    async def update_item_status(self, item_id: ObjectId, status: ItemStatus, 
                               error_message: Optional[str] = None, 
                               processing_step: Optional[Dict[str, Any]] = None) -> bool:
        """更新条目状态"""
        try:
            item = await KnowledgeItem.get(item_id)
            if not item:
                return False
            
            item.status = status
            if error_message:
                item.error_message = error_message
            
            if processing_step:
                item.add_processing_step(
                    processing_step.get("step_name", ""),
                    processing_step.get("status", ""),
                    processing_step.get("details")
                )
            
            if status == ItemStatus.COMPLETED:
                item.processed_at = datetime.now(timezone.utc)
            
            item.update_timestamp()
            await item.save()
            
            logger.info(f"Updated status of item {item_id} to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update status for item {item_id}: {e}")
            return False
    
    async def get_item(self, item_id: ObjectId, include_links: bool = True) -> Optional[KnowledgeItem]:
        """获取知识条目"""
        try:
            item = await KnowledgeItem.get(item_id)
            if item and include_links:
                await item.fetch_all_links()
            return item
        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
            return None
    
    async def list_items(self, skip: int = 0, limit: int = 10, 
                        filters: Optional[Dict[str, Any]] = None) -> List[KnowledgeItem]:
        """列出知识条目"""
        try:
            query = KnowledgeItem.find(KnowledgeItem.is_deleted == False)
            
            if filters:
                if filters.get("status"):
                    query = query.find(KnowledgeItem.status == filters["status"])
                if filters.get("knowledge_type"):
                    query = query.find(KnowledgeItem.knowledge_type == filters["knowledge_type"])
                if filters.get("tenant_id"):
                    query = query.find(KnowledgeItem.tenant_id == filters["tenant_id"])
                if filters.get("created_by"):
                    query = query.find(KnowledgeItem.created_by == filters["created_by"])
            
            return await query.skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to list items: {e}")
            return []
    
    async def search_items(self, query: str, skip: int = 0, limit: int = 10) -> List[KnowledgeItem]:
        """搜索知识条目"""
        try:
            # 使用文本搜索
            return await KnowledgeItem.find(
                {"$text": {"$search": query}},
                KnowledgeItem.is_deleted == False
            ).skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to search items: {e}")
            return []
    
    async def delete_item(self, item_id: ObjectId) -> bool:
        """删除知识条目（软删除）"""
        try:
            item = await KnowledgeItem.get(item_id)
            if not item:
                return False
            
            # 软删除
            item.mark_as_deleted()
            await item.save()
            
            # 删除关联的内容（可选）
            # await self._delete_associated_content(item_id)
            
            logger.info(f"Soft deleted knowledge item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            return False
    
    async def _delete_associated_content(self, item_id: ObjectId):
        """删除关联的内容"""
        # 实现内容删除逻辑
        pass

class KnowledgeBaseService:
    async def create_base(self, name: str, description: Optional[str] = None,
                         user_id: str = "", tenant_id: Optional[str] = None,
                         access_level: AccessLevel = AccessLevel.USER,
                         tags: Optional[List[str]] = None,
                         category: Optional[str] = None) -> KnowledgeBase:
        """创建知识库"""
        try:
            base = KnowledgeBase(
                name=name,
                description=description,
                category=category,
                access_level=access_level,
                tenant_id=tenant_id,
                created_by=user_id,
                updated_by=user_id
            )
            
            await base.insert()
            
            # 批量添加标签
            if tags:
                await self._update_base_tags(base, tags, user_id)
            
            logger.info(f"Created knowledge base {base.id} by user {user_id}")
            return base
            
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            raise
    
    async def update_base(self, base_id: ObjectId, name: str, description: Optional[str] = None,
                         updated_by: str=None, access_level: Optional[AccessLevel] = None,
                         tags: Optional[List[str]] = None, category: Optional[str] = None) -> Optional[KnowledgeBase]:
        """更新知识库"""
        try:
            base = await KnowledgeBase.get(base_id)
            if not base:
                logger.warning(f"Knowledge base {base_id} not found")
                return None
            
            base.name = name
            base.description = description
            base.category = category
            base.updated_by = updated_by
            
            if access_level:
                base.access_level = access_level
            
            base.update_timestamp()
            
            # 更新标签
            if tags is not None:
                await self._update_base_tags(base, tags, updated_by)
            
            await base.save()
            
            logger.info(f"Updated knowledge base {base_id} by user {updated_by}")
            return base
            
        except Exception as e:
            logger.error(f"Failed to update knowledge base {base_id}: {e}")
            raise
    
    async def _update_base_tags(self, base: KnowledgeBase, tags: List[str], user_id: str):
        """更新知识库标签"""
        try:
            # 获取当前标签
            current_tags = await tag_service.get_object_tags("knowledge_base", str(base.id))
            current_tag_names = [tag.name for tag in current_tags]
            
            # 需要添加的标签
            tags_to_add = [tag for tag in tags if tag not in current_tag_names]
            # 需要移除的标签
            tags_to_remove = [tag for tag in current_tag_names if tag not in tags]
            
            # 批量添加新标签
            if tags_to_add:
                await tag_utils.batch_tag_objects(
                    tags_to_add, "knowledge_base", str(base.id), user_id
                )
            
            # 批量移除标签
            if tags_to_remove:
                await tag_utils.batch_untag_objects(
                    tags_to_remove, "knowledge_base", str(base.id)
                )
            
            # 重新加载标签引用
            await base.fetch_all_links()
            
        except Exception as e:
            logger.error(f"Failed to update tags for base {base.id}: {e}")
            raise
    
    async def add_item_to_base(self, base_id: ObjectId, item_id: ObjectId) -> bool:
        """添加条目到知识库"""
        try:
            base = await KnowledgeBase.get(base_id)
            item = await KnowledgeItem.get(item_id)
            
            if not base or not item:
                return False
            
            base.add_item(item)
            await base.save()
            
            # 也更新条目的知识库引用
            if base.id not in [kb.id for kb in item.knowledge_bases]:
                item.knowledge_bases.append(base)
                await item.save()
            
            logger.info(f"Added item {item_id} to base {base_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add item {item_id} to base {base_id}: {e}")
            return False
    
    async def remove_item_from_base(self, base_id: ObjectId, item_id: ObjectId) -> bool:
        """从知识库移除条目"""
        try:
            base = await KnowledgeBase.get(base_id)
            item = await KnowledgeItem.get(item_id)
            
            if not base or not item:
                return False
            
            base.remove_item(item)
            await base.save()
            
            # 也更新条目的知识库引用
            item.knowledge_bases = [kb for kb in item.knowledge_bases if kb.id != base.id]
            await item.save()
            
            logger.info(f"Removed item {item_id} from base {base_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item {item_id} from base {base_id}: {e}")
            return False
    
    async def get_base(self, base_id: ObjectId, include_links: bool = True) -> Optional[KnowledgeBase]:
        """获取知识库"""
        try:
            base = await KnowledgeBase.get(base_id)
            if base and include_links:
                await base.fetch_all_links()
            return base
        except Exception as e:
            logger.error(f"Failed to get base {base_id}: {e}")
            return None
    
    async def list_bases(self, skip: int = 0, limit: int = 10,
                        filters: Optional[Dict[str, Any]] = None) -> List[KnowledgeBase]:
        """列出知识库"""
        try:
            query = KnowledgeBase.find(KnowledgeBase.is_deleted == False)
            
            if filters:
                if filters.get("tenant_id"):
                    query = query.find(KnowledgeBase.tenant_id == filters["tenant_id"])
                if filters.get("created_by"):
                    query = query.find(KnowledgeBase.created_by == filters["created_by"])
                if filters.get("access_level"):
                    query = query.find(KnowledgeBase.access_level == filters["access_level"])
                if filters.get("is_active"):
                    query = query.find(KnowledgeBase.is_active == filters["is_active"])
            
            return await query.skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to list bases: {e}")
            return []
    
    async def delete_base(self, base_id: ObjectId) -> bool:
        """删除知识库（软删除）"""
        try:
            base = await KnowledgeBase.get(base_id)
            if not base:
                return False
            
            # 软删除
            base.mark_as_deleted()
            await base.save()
            
            logger.info(f"Soft deleted knowledge base {base_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete base {base_id}: {e}")
            return False

# 全局服务实例
knowledge_item_service = KnowledgeItemService()
knowledge_base_service = KnowledgeBaseService()