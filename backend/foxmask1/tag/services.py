from .models import Tag, TaggedObject, TagUsageStats, TagCollection, TagTypeEnum
from typing import List, Optional, Dict, Any
from bson import ObjectId
from uuid import UUID
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TagService:
    async def create_tag(self, name: str, user_id: str, 
                        tag_type: TagTypeEnum = TagTypeEnum.USER,
                        description: Optional[Dict[str, str]] = None,
                        color: Optional[str] = None,
                        icon: Optional[str] = None,
                        parent_id: Optional[ObjectId] = None,
                        is_public: bool = True,
                        tenant_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Tag:
        """创建标签"""
        try:
            # 生成slug
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            
            tag = Tag(
                name=name,
                slug=slug,
                tag_type=tag_type,
                display_name={"zh-CN": name, "en-US": name},
                description=description or {"zh-CN": "", "en-US": ""},
                color=color or "#6B7280",
                icon=icon,
                parent_id=parent_id,
                is_public=is_public,
                tenant_id=tenant_id,
                owner_id=user_id,
                created_by=user_id,
                updated_by=user_id,
                metadata=metadata or {}
            )
            
            await tag.insert()
            logger.info(f"Created tag {tag.id} by user {user_id}")
            return tag
            
        except Exception as e:
            logger.error(f"Failed to create tag: {e}")
            raise
    
    async def update_tag(self, tag_id: ObjectId, user_id: str,
                        name: Optional[str] = None,
                        description: Optional[Dict[str, str]] = None,
                        color: Optional[str] = None,
                        icon: Optional[str] = None,
                        parent_id: Optional[ObjectId] = None,
                        is_public: Optional[bool] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[Tag]:
        """更新标签"""
        try:
            tag = await Tag.get(tag_id)
            if not tag:
                logger.warning(f"Tag {tag_id} not found")
                return None
            
            if name is not None:
                tag.name = name
                # 更新slug
                import re
                tag.slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                # 更新显示名称
                tag.display_name = {**tag.display_name, "zh-CN": name, "en-US": name}
            
            if description is not None:
                tag.description = {**tag.description, **description}
            
            if color is not None:
                tag.color = color
            
            if icon is not None:
                tag.icon = icon
            
            if parent_id is not None:
                tag.parent_id = parent_id
            
            if is_public is not None:
                tag.is_public = is_public
            
            if metadata is not None:
                tag.metadata = {**tag.metadata, **metadata}
            
            tag.updated_by = user_id
            tag.update_timestamp()
            await tag.save()
            
            logger.info(f"Updated tag {tag_id} by user {user_id}")
            return tag
            
        except Exception as e:
            logger.error(f"Failed to update tag {tag_id}: {e}")
            raise
    
    async def get_tag(self, tag_id: ObjectId) -> Optional[Tag]:
        """根据ID获取标签"""
        try:
            return await Tag.get(tag_id)
        except Exception as e:
            logger.error(f"Failed to get tag {tag_id}: {e}")
            return None
    
    async def get_tag_by_name(self, name: str, tenant_id: Optional[str] = None) -> Optional[Tag]:
        """根据名称获取标签"""
        try:
            if tenant_id:
                return await Tag.find_one(Tag.name == name, Tag.tenant_id == tenant_id)
            else:
                return await Tag.find_one(Tag.name == name)
        except Exception as e:
            logger.error(f"Failed to get tag by name {name}: {e}")
            return None
    
    async def get_tag_by_slug(self, slug: str, tenant_id: Optional[str] = None) -> Optional[Tag]:
        """根据slug获取标签"""
        try:
            if tenant_id:
                return await Tag.find_one(Tag.slug == slug, Tag.tenant_id == tenant_id)
            else:
                return await Tag.find_one(Tag.slug == slug)
        except Exception as e:
            logger.error(f"Failed to get tag by slug {slug}: {e}")
            return None
    
    async def list_tags(self, skip: int = 0, limit: int = 10,
                       filters: Optional[Dict[str, Any]] = None) -> List[Tag]:
        """列出标签（支持过滤）"""
        try:
            query = Tag.find(Tag.is_deleted == False)
            
            if filters:
                if filters.get("tag_type"):
                    query = query.find(Tag.tag_type == filters["tag_type"])
                if filters.get("tenant_id"):
                    query = query.find(Tag.tenant_id == filters["tenant_id"])
                if filters.get("is_public"):
                    query = query.find(Tag.is_public == filters["is_public"])
                if filters.get("created_by"):
                    query = query.find(Tag.created_by == filters["created_by"])
                if filters.get("parent_id"):
                    query = query.find(Tag.parent_id == filters["parent_id"])
            
            return await query.skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to list tags: {e}")
            return []
    
    async def search_tags(self, query: str, skip: int = 0, limit: int = 10,
                         tenant_id: Optional[str] = None) -> List[Tag]:
        """搜索标签"""
        try:
            search_query = {"$text": {"$search": query}}
            if tenant_id:
                search_query["tenant_id"] = tenant_id
            
            return await Tag.find(search_query, Tag.is_deleted == False)\
                          .skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to search tags: {e}")
            return []
    
    async def delete_tag(self, tag_id: ObjectId) -> bool:
        """删除标签（软删除）"""
        try:
            tag = await Tag.get(tag_id)
            if not tag:
                return False
            
            # 软删除
            tag.mark_as_deleted()
            await tag.save()
            
            # 删除所有相关的标记关系
            await TaggedObject.find(TaggedObject.tag_id == tag_id).delete()
            
            logger.info(f"Soft deleted tag {tag_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tag {tag_id}: {e}")
            return False
    
    async def tag_object(self, tag_id: ObjectId, object_type: str,
                        object_id: ObjectId, user_id: str,
                        weight: float = 1.0, context: Optional[Dict[str, Any]] = None,
                        source: str = "manual") -> Optional[TaggedObject]:
        """标记对象"""
        try:
            # 检查标签是否存在
            tag = await Tag.get(tag_id)
            if not tag or tag.is_deleted:
                logger.warning(f"Tag {tag_id} not found or deleted")
                return None
            
            # 检查是否已标记
            existing = await TaggedObject.find_one(
                TaggedObject.tag_id == tag_id,
                TaggedObject.object_type == object_type,
                TaggedObject.object_id == object_id,
                TaggedObject.is_active == True
            )
            
            if existing:
                return existing
            
            # 创建新的标记关系
            tagged_object = TaggedObject(
                tag_id=tag_id,
                object_type=object_type,
                object_id=object_id,
                tagged_by=user_id,
                weight=weight,
                context=context,
                source=source
            )
            await tagged_object.insert()
            
            # 更新标签使用计数
            tag.increment_usage(weight)
            await tag.save()
            
            # 更新使用统计
            await self._update_usage_stats(tag_id, object_type)
            
            logger.info(f"Tagged object {object_type}:{object_id} with tag {tag_id} by user {user_id}")
            return tagged_object
            
        except Exception as e:
            logger.error(f"Failed to tag object: {e}")
            return None
    
    async def untag_object(self, tag_id: ObjectId, object_type: str, object_id: ObjectId) -> bool:
        """取消标记对象"""
        try:
            tagged_object = await TaggedObject.find_one(
                TaggedObject.tag_id == tag_id,
                TaggedObject.object_type == object_type,
                TaggedObject.object_id == object_id,
                TaggedObject.is_active == True
            )
            
            if tagged_object:
                # 软删除标记关系
                tagged_object.is_active = False
                await tagged_object.save()
                
                # 更新标签使用计数
                tag = await Tag.get(tag_id)
                if tag and tag.usage_count > 0:
                    tag.usage_count = max(0, tag.usage_count - 1)
                    await tag.save()
                
                logger.info(f"Untagged object {object_type}:{object_id} from tag {tag_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to untag object: {e}")
            return False
    
    async def get_object_tags(self, object_type: str, object_id: ObjectId,
                            active_only: bool = True) -> List[Tag]:
        """获取对象的标签"""
        try:
            query = {
                "object_type": object_type,
                "object_id": object_id
            }
            if active_only:
                query["is_active"] = True
            
            tagged_objects = await TaggedObject.find(query).to_list()
            
            tag_ids = [to.tag_id for to in tagged_objects]
            if not tag_ids:
                return []
            
            return await Tag.find({"_id": {"$in": tag_ids}, "is_deleted": False}).to_list()
        except Exception as e:
            logger.error(f"Failed to get object tags: {e}")
            return []
    
    async def get_tagged_objects(self, tag_id: ObjectId, object_type: Optional[str] = None,
                                active_only: bool = True, skip: int = 0, limit: int = 10) -> List[TaggedObject]:
        """获取标记的对象"""
        try:
            query = {"tag_id": tag_id}
            if object_type:
                query["object_type"] = object_type
            if active_only:
                query["is_active"] = True
            
            return await TaggedObject.find(query).skip(skip).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to get tagged objects: {e}")
            return []
    
    async def get_popular_tags(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[Tag]:
        """获取热门标签"""
        try:
            query = Tag.find(Tag.is_deleted == False)
            if tenant_id:
                query = query.find(Tag.tenant_id == tenant_id)
            
            return await query.sort(-Tag.usage_count).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to get popular tags: {e}")
            return []
    
    async def get_related_tags(self, tag_id: ObjectId, limit: int = 10) -> List[Tag]:
        """获取相关标签"""
        try:
            # 这里可以实现基于共现分析的推荐算法
            # 暂时返回空列表
            return []
        except Exception as e:
            logger.error(f"Failed to get related tags: {e}")
            return []
    
    async def _update_usage_stats(self, tag_id: ObjectId, object_type: str):
        """更新使用统计"""
        try:
            # 这里可以实现详细的统计更新逻辑
            pass
        except Exception as e:
            logger.error(f"Failed to update usage stats: {e}")
    
    async def batch_tag_objects(self, tag_names: List[str], object_type: str,
                              object_id: ObjectId, user_id: str) -> List[ObjectId]:
        """批量标记对象"""
        try:
            tagged_ids = []
            for tag_name in tag_names:
                # 查找或创建标签
                tag = await self.get_tag_by_name(tag_name)
                if not tag:
                    tag = await self.create_tag(
                        name=tag_name,
                        user_id=user_id,
                        tag_type=TagTypeEnum.USER
                    )
                
                # 标记对象
                tagged_object = await self.tag_object(
                    tag_id=tag.id,
                    object_type=object_type,
                    object_id=object_id,
                    user_id=user_id
                )
                
                if tagged_object:
                    tagged_ids.append(tag.id)
            
            return tagged_ids
            
        except Exception as e:
            logger.error(f"Failed to batch tag objects: {e}")
            return []
    
    async def batch_untag_objects(self, tag_names: List[str], object_type: str, object_id: ObjectId) -> bool:
        """批量取消标记对象"""
        try:
            success = True
            for tag_name in tag_names:
                tag = await self.get_tag_by_name(tag_name)
                if tag:
                    result = await self.untag_object(
                        tag_id=tag.id,
                        object_type=object_type,
                        object_id=object_id
                    )
                    success = success and result
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to batch untag objects: {e}")
            return False

# 全局标签服务实例
tag_service = TagService()