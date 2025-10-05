# -*- coding: utf-8 -*-
# foxmask/file/repository/file_repository.py
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from beanie.operators import In, Eq, GTE, LTE, RegEx, And
from pymongo import ASCENDING, DESCENDING

from foxmask.core.mongo import mongodb
from foxmask.file.models.management import File, FileLog
from foxmask.file.enums import FileTypeEnum, UploadProcStatusEnum


class FileRepository:
    """文件数据仓库 - 直接数据操作"""
    
    def __init__(self):
        self.database = mongodb.database
    
    async def get_by_id(self, file_id: str) -> Optional[File]:
        """根据ID获取文件"""
        return await File.get(file_id)
    
    async def get_by_uid(self, uid: str) -> Optional[File]:
        """根据UID获取文件"""
        return await File.find_one(File.uid == uid)
    
    async def get_by_filename(self, tenant_id: str, filename: str) -> Optional[File]:
        """根据文件名获取文件"""
        return await File.find_one(
            And(
                Eq(File.tenant_id, tenant_id),
                Eq(File.original_filename, filename)
            )
        )
    
    async def get_by_storage_key(self, tenant_id: str, storage_key: str) -> Optional[File]:
        """根据存储键获取文件"""
        return await File.find_one(
            And(
                Eq(File.tenant_id, tenant_id),
                Eq(File.storage_key, storage_key)
            )
        )
    
    async def create_file(self, file_data: Dict[str, Any]) -> File:
        """创建新文件"""
        file = File(**file_data)
        await file.insert()
        return file
    
    async def update_file(self, file_id: str, update_data: Dict[str, Any]) -> Optional[File]:
        """更新文件信息"""
        file = await self.get_by_id(file_id)
        if file:
            for field, value in update_data.items():
                if hasattr(file, field):
                    setattr(file, field, value)
            await file.save()
            return file
        return None
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        file = await self.get_by_id(file_id)
        if file:
            await file.delete()
            return True
        return False
    
    async def list_files(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        **filters
    ) -> Tuple[List[File], int]:
        """获取文件列表"""
        query = self._build_query(tenant_id, filters)
        
        # 获取总数
        total = await File.find(query).count()
        
        # 构建排序
        sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
        
        # 获取分页数据
        files = await File.find(query).skip(skip).limit(limit).sort((sort_field, sort_dir)).to_list()
        
        return files, total
    
    async def list_by_file_type(self, tenant_id: str, file_type: FileTypeEnum, limit: int = 100) -> List[File]:
        """根据文件类型获取文件列表"""
        return await File.find(
            And(
                Eq(File.tenant_id, tenant_id),
                Eq(File.file_type, file_type),
                Eq(File.status, "active")
            )
        ).limit(limit).sort(("created_at", DESCENDING)).to_list()
    
    async def list_by_status(self, tenant_id: str, file_status: UploadProcStatusEnum, limit: int = 100) -> List[File]:
        """根据文件状态获取文件列表"""
        return await File.find(
            And(
                Eq(File.tenant_id, tenant_id),
                Eq(File.file_status, file_status)
            )
        ).limit(limit).sort(("created_at", DESCENDING)).to_list()
    
    async def increment_download_count(self, file_id: str) -> Optional[File]:
        """增加文件下载次数"""
        file = await self.get_by_id(file_id)
        if file:
            file.download_count += 1
            await file.save()
            return file
        return None
    
    async def update_file_status(self, file_id: str, status: UploadProcStatusEnum, error_info: Dict[str, Any] = None) -> Optional[File]:
        """更新文件状态"""
        update_data = {"file_status": status}
        if error_info:
            update_data["error_info"] = error_info
        
        return await self.update_file(file_id, update_data)
    
    async def get_file_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取文件统计信息"""
        # 总文件数和大小
        total_files = await File.find(Eq(File.tenant_id, tenant_id)).count()
        
        # 按文件类型统计
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {
                "_id": "$file_type",
                "count": {"$sum": 1},
                "total_size": {"$sum": "$file_size"}
            }}
        ]
        
        stats_by_type = {}
        async for result in File.aggregate(pipeline):
            stats_by_type[result["_id"]] = {
                "count": result["count"],
                "total_size": result["total_size"]
            }
        
        # 按状态统计
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {
                "_id": "$file_status",
                "count": {"$sum": 1}
            }}
        ]
        
        stats_by_status = {}
        async for result in File.aggregate(pipeline):
            stats_by_status[result["_id"]] = result["count"]
        
        # 总文件大小
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {
                "_id": None,
                "total_size": {"$sum": "$file_size"}
            }}
        ]
        
        total_size = 0
        async for result in File.aggregate(pipeline):
            total_size = result["total_size"]
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "by_file_type": stats_by_type,
            "by_status": stats_by_status
        }
    
    def _build_query(self, tenant_id: str, filters: Dict[str, Any]) -> Any:
        """构建查询条件"""
        query_filters = [Eq(File.tenant_id, tenant_id)]
        
        if filters.get("title"):
            query_filters.append(RegEx(File.title, f".*{filters['title']}.*", "i"))
        
        if filters.get("original_filename"):
            query_filters.append(RegEx(File.original_filename, f".*{filters['original_filename']}.*", "i"))
        
        if filters.get("file_type"):
            query_filters.append(Eq(File.file_type, filters["file_type"]))
        
        if filters.get("file_status"):
            query_filters.append(Eq(File.file_status, filters["file_status"]))
        
        if filters.get("content_type"):
            query_filters.append(RegEx(File.content_type, f".*{filters['content_type']}.*", "i"))
        
        if filters.get("category"):
            query_filters.append(Eq(File.category, filters["category"]))
        
        if filters.get("tags"):
            query_filters.append(In(File.tags, filters["tags"]))
        
        if filters.get("created_by"):
            query_filters.append(Eq(File.created_by, filters["created_by"]))
        
        if filters.get("visibility"):
            query_filters.append(Eq(File.visibility, filters["visibility"]))
        
        if filters.get("min_size") is not None:
            query_filters.append(GTE(File.file_size, filters["min_size"]))
        
        if filters.get("max_size") is not None:
            query_filters.append(LTE(File.file_size, filters["max_size"]))
        
        if filters.get("start_date"):
            query_filters.append(GTE(File.created_at, filters["start_date"].isoformat()))
        
        if filters.get("end_date"):
            query_filters.append(LTE(File.created_at, filters["end_date"].isoformat()))
        
        return And(*query_filters) if len(query_filters) > 1 else query_filters[0]


class FileLogRepository:
    """文件日志数据仓库 - 直接数据操作"""
    
    def __init__(self):
        self.database = mongodb.database
    
    async def create_log(self, log_data: Dict[str, Any]) -> FileLog:
        """创建文件操作日志"""
        log = FileLog(**log_data)
        await log.insert()
        return log
    
    async def get_logs_by_file(self, file_id: str, limit: int = 100) -> List[FileLog]:
        """根据文件ID获取操作日志"""
        return await FileLog.find(
            Eq(FileLog.master_id, file_id)
        ).limit(limit).sort(("operation_time", DESCENDING)).to_list()
    
    async def get_logs_by_operation(self, tenant_id: str, operation: str, limit: int = 100) -> List[FileLog]:
        """根据操作类型获取日志"""
        return await FileLog.find(
            And(
                Eq(FileLog.tenant_id, tenant_id),
                Eq(FileLog.operation, operation)
            )
        ).limit(limit).sort(("operation_time", DESCENDING)).to_list()
    
    async def list_logs(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        sort_field: str = "operation_time",
        sort_order: str = "desc",
        **filters
    ) -> Tuple[List[FileLog], int]:
        """获取日志列表"""
        query = self._build_query(tenant_id, filters)
        
        # 获取总数
        total = await FileLog.find(query).count()
        
        # 构建排序
        sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
        
        # 获取分页数据
        logs = await FileLog.find(query).skip(skip).limit(limit).sort((sort_field, sort_dir)).to_list()
        
        return logs, total
    
    async def get_operation_stats(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """获取操作统计信息"""
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = start_date.replace(day=start_date.day - days)
        
        # 按操作类型统计
        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "operation_time": {"$gte": start_date}
            }},
            {"$group": {
                "_id": "$operation",
                "count": {"$sum": 1}
            }}
        ]
        
        stats_by_operation = {}
        async for result in FileLog.aggregate(pipeline):
            stats_by_operation[result["_id"]] = result["count"]
        
        # 按用户统计
        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "operation_time": {"$gte": start_date}
            }},
            {"$group": {
                "_id": "$operated_by",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        stats_by_user = {}
        async for result in FileLog.aggregate(pipeline):
            stats_by_user[result["_id"]] = result["count"]
        
        return {
            "total_operations": sum(stats_by_operation.values()),
            "by_operation_type": stats_by_operation,
            "by_user": stats_by_user
        }
    
    def _build_query(self, tenant_id: str, filters: Dict[str, Any]) -> Any:
        """构建查询条件"""
        query_filters = [Eq(FileLog.tenant_id, tenant_id)]
        
        if filters.get("operation"):
            query_filters.append(Eq(FileLog.operation, filters["operation"]))
        
        if filters.get("operated_by"):
            query_filters.append(Eq(FileLog.operated_by, filters["operated_by"]))
        
        if filters.get("master_id"):
            query_filters.append(Eq(FileLog.master_id, filters["master_id"]))
        
        if filters.get("start_date"):
            query_filters.append(GTE(FileLog.operation_time, filters["start_date"]))
        
        if filters.get("end_date"):
            query_filters.append(LTE(FileLog.operation_time, filters["end_date"]))
        
        return And(*query_filters) if len(query_filters) > 1 else query_filters[0]