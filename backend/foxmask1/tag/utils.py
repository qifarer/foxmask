from typing import List, Dict, Any
from bson import ObjectId
from .services import tag_service

class TagUtils:
    async def batch_tag_objects(self, tag_names: List[str], object_type: str, 
                              object_id: ObjectId, user_id: str) -> List[str]:
        """
        批量标记对象，如果标签不存在则创建
        """
        tagged_ids = []
        
        for tag_name in tag_names:
            # 查找或创建标签
            tag = await tag_service.get_tag_by_name(tag_name)
            if not tag:
                tag = await tag_service.create_tag(
                    name=tag_name,
                    tag_type="user",  # 默认用户标签
                    user_id=user_id
                )
            
            # 标记对象
            tagged_object = await tag_service.tag_object(
                tag.id,
                object_type,
                object_id,
                user_id
            )
            
            tagged_ids.append(str(tagged_object.id))
        
        return tagged_ids
    
    async def batch_untag_objects(self, tag_names: List[str], object_type: str, 
                                object_id: ObjectId) -> int:
        """
        批量取消标记对象
        """
        untagged_count = 0
        
        for tag_name in tag_names:
            # 查找标签
            tag = await tag_service.get_tag_by_name(tag_name)
            if tag:
                # 取消标记
                success = await tag_service.untag_object(
                    tag.id,
                    object_type,
                    object_id
                )
                if success:
                    untagged_count += 1
        
        return untagged_count
    
    async def get_objects_by_tags(self, tag_names: List[str], object_type: str, 
                                skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """
        根据标签名称获取对象列表
        """
        # 获取标签ID
        tag_ids = []
        for tag_name in tag_names:
            tag = await tag_service.get_tag_by_name(tag_name)
            if tag:
                tag_ids.append(tag.id)
        
        if not tag_ids:
            return []
        
        # 获取标记的对象
        tagged_objects = []
        for tag_id in tag_ids:
            objects = await tag_service.get_tagged_objects(tag_id, object_type, skip, limit)
            tagged_objects.extend(objects)
        
        # 去重并返回
        seen = set()
        unique_objects = []
        for obj in tagged_objects:
            if obj.object_id not in seen:
                seen.add(obj.object_id)
                unique_objects.append({
                    "object_type": obj.object_type,
                    "object_id": obj.object_id,
                    "tagged_at": obj.tagged_at
                })
        
        return unique_objects

# 全局标签工具实例
tag_utils = TagUtils()