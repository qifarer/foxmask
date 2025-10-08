from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from beanie import PydanticObjectId
from beanie.operators import And, Or, In, RegEx, GTE, LTE
from foxmask.file.models.management import File, FileLog
from foxmask.core.enums import Status
from foxmask.file.enums import FileTypeEnum, FileProcStatusEnum
from foxmask.utils.helpers import get_current_timestamp

class FileRepository:
    """文件仓库类 - 专注于File模型的数据操作"""
    
    async def create(self, file: File) -> File:
        """创建文件记录"""
        await file.insert()
        return file
    
    async def get_by_uid(self, uid: str, tenant_id: str) -> Optional[File]:
        """根据UID获取文件"""
        return await File.find_one(
            File.uid == uid, 
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED
        )
    
    async def get_by_id(self, object_id: PydanticObjectId) -> Optional[File]:
        """根据ObjectId获取文件"""
        return await File.get(object_id)
    
    async def save(self, file: File) -> File:
        """保存文件（更新或创建）"""
        await file.save()
        return file
    
    async def delete(self, file: File) -> bool:
        """删除文件"""
        await file.delete()
        return True
    
    async def soft_delete(self, file: File) -> bool:
        """软删除文件"""
        file.status = Status.ARCHIVED
        file.archived_at = get_current_timestamp()
        file.updated_at = get_current_timestamp()
        await file.save()
        return True
    
    async def find_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[File]:
        """根据租户ID查找文件"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def find_by_filename(self, tenant_id: str, filename: str) -> Optional[File]:
        """根据文件名查找文件"""
        return await File.find_one(
            File.tenant_id == tenant_id,
            File.filename == filename,
            File.status != Status.ARCHIVED
        )
    
    async def find_by_storage_path(self, storage_bucket: str, storage_path: str) -> Optional[File]:
        """根据存储路径查找文件"""
        return await File.find_one(
            File.storage_bucket == storage_bucket,
            File.storage_path == storage_path,
            File.status != Status.ARCHIVED
        )
    
    async def find_by_file_type(self, tenant_id: str, file_type: FileTypeEnum, 
                              skip: int = 0, limit: int = 100) -> List[File]:
        """根据文件类型查找"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.file_type == file_type,
            File.status != Status.ARCHIVED
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def find_by_status(self, tenant_id: str, status: Status, 
                           skip: int = 0, limit: int = 100) -> List[File]:
        """根据状态查找文件"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.status == status
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def find_by_proc_status(self, tenant_id: str, proc_status: FileProcStatusEnum,
                                skip: int = 0, limit: int = 100) -> List[File]:
        """根据处理状态查找文件"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.proc_status == proc_status,
            File.status != Status.ARCHIVED
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def find_by_tags(self, tenant_id: str, tags: List[str], 
                         skip: int = 0, limit: int = 100) -> List[File]:
        """根据标签查找文件"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED,
            In(File.tags, tags)
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def find_by_creator(self, tenant_id: str, created_by: str,
                            skip: int = 0, limit: int = 100) -> List[File]:
        """根据创建者查找文件"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.created_by == created_by,
            File.status != Status.ARCHIVED
        ).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def search_files(self, tenant_id: str, keyword: str, 
                         skip: int = 0, limit: int = 100) -> List[File]:
        """搜索文件"""
        query = And(
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED,
            Or(
                RegEx(File.filename, keyword, "i"),
                RegEx(File.title, keyword, "i"),
                RegEx(File.desc, keyword, "i")
            )
        )
        return await File.find(query).sort(-File.created_at).skip(skip).limit(limit).to_list()
    
    async def advanced_search(self, tenant_id: str, **filters) -> List[File]:
        """高级搜索"""
        conditions = [
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED
        ]
        
        # 动态构建查询条件
        for field, value in filters.items():
            if value is not None:
                if hasattr(File, field):
                    if isinstance(value, str) and field in ['filename', 'title', 'desc', 'content_type']:
                        conditions.append(RegEx(getattr(File, field), value, "i"))
                    elif isinstance(value, list) and field == 'tags':
                        conditions.append(In(getattr(File, field), value))
                    else:
                        conditions.append(getattr(File, field) == value)
        
        query = And(*conditions) if len(conditions) > 1 else conditions[0]
        return await File.find(query).sort(-File.created_at).to_list()
    
    async def count_by_tenant(self, tenant_id: str) -> int:
        """统计租户的文件数量"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.status != Status.ARCHIVED
        ).count()
    
    async def count_by_file_type(self, tenant_id: str, file_type: FileTypeEnum) -> int:
        """统计指定类型的文件数量"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.file_type == file_type,
            File.status != Status.ARCHIVED
        ).count()
    
    async def count_by_status(self, tenant_id: str, status: Status) -> int:
        """统计指定状态的文件数量"""
        return await File.find(
            File.tenant_id == tenant_id,
            File.status == status
        ).count()
    
    async def get_total_size_by_tenant(self, tenant_id: str) -> int:
        """获取租户文件总大小"""
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "status": {"$ne": Status.ARCHIVED.value}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_size": {"$sum": "$file_size"}
                }
            }
        ]
        
        result = await File.aggregate(pipeline).to_list()
        return result[0]["total_size"] if result else 0
    
    async def increment_download_count(self, file: File) -> File:
        """增加文件下载次数"""
        file.download_count += 1
        file.updated_at = get_current_timestamp()
        await file.save()
        return file
    
    async def update_proc_status(self, file: File, proc_status: FileProcStatusEnum, 
                               proc_meta: Optional[Dict[str, Any]] = None) -> File:
        """更新文件处理状态"""
        file.proc_status = proc_status
        file.updated_at = get_current_timestamp()
        
        if proc_meta is not None:
            file.proc_meta = proc_meta
        
        await file.save()
        return file
    
    async def bulk_update_proc_status(self, files: List[File], proc_status: FileProcStatusEnum) -> int:
        """批量更新文件处理状态"""
        updated_count = 0
        for file in files:
            file.proc_status = proc_status
            file.updated_at = get_current_timestamp()
            await file.save()
            updated_count += 1
        
        return updated_count


class FileLogRepository:
    """文件日志仓库类 - 专注于FileLog模型的数据操作"""
    
    async def create(self, file_log: FileLog) -> FileLog:
        """创建文件日志"""
        await file_log.insert()
        return file_log
    
    async def get_by_id(self, object_id: PydanticObjectId) -> Optional[FileLog]:
        """根据ObjectId获取日志"""
        return await FileLog.get(object_id)
    
    async def get_by_master_id(self, master_id: str, tenant_id: str, 
                             skip: int = 0, limit: int = 100) -> List[FileLog]:
        """根据文件ID获取操作日志"""
        return await FileLog.find(
            FileLog.master_id == master_id,
            FileLog.tenant_id == tenant_id
        ).sort(-FileLog.operation_time).skip(skip).limit(limit).to_list()
    
    async def get_by_operation(self, tenant_id: str, operation: str,
                             skip: int = 0, limit: int = 100) -> List[FileLog]:
        """根据操作类型获取日志"""
        return await FileLog.find(
            FileLog.tenant_id == tenant_id,
            FileLog.operation == operation
        ).sort(-FileLog.operation_time).skip(skip).limit(limit).to_list()
    
    async def get_by_operator(self, tenant_id: str, operated_by: str,
                            skip: int = 0, limit: int = 100) -> List[FileLog]:
        """根据操作者获取日志"""
        return await FileLog.find(
            FileLog.tenant_id == tenant_id,
            FileLog.operated_by == operated_by
        ).sort(-FileLog.operation_time).skip(skip).limit(limit).to_list()
    
    async def get_recent_operations(self, tenant_id: str, limit: int = 50) -> List[FileLog]:
        """获取最近的操作日志"""
        return await FileLog.find(
            FileLog.tenant_id == tenant_id
        ).sort(-FileLog.operation_time).limit(limit).to_list()
    
    async def count_by_master_id(self, master_id: str, tenant_id: str) -> int:
        """统计文件的日志数量"""
        return await FileLog.find(
            FileLog.master_id == master_id,
            FileLog.tenant_id == tenant_id
        ).count()
    
    async def count_by_operation(self, tenant_id: str, operation: str) -> int:
        """统计指定操作的日志数量"""
        return await FileLog.find(
            FileLog.tenant_id == tenant_id,
            FileLog.operation == operation
        ).count()


class FileStatisticsService:
    """文件统计服务 - 专注于统计相关的数据操作"""
    
    def __init__(self, file_repo: FileRepository):
        self.file_repo = file_repo
    
    async def get_tenant_statistics(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户文件统计"""
        # 获取基本统计
        total_files = await self.file_repo.count_by_tenant(tenant_id)
        total_size = await self.file_repo.get_total_size_by_tenant(tenant_id)
        
        # 获取文件类型分布
        file_type_distribution = {}
        for file_type in FileTypeEnum:
            count = await self.file_repo.count_by_file_type(tenant_id, file_type)
            if count > 0:
                file_type_distribution[file_type] = count
        
        # 获取状态分布
        status_distribution = {}
        for status in Status:
            count = await self.file_repo.count_by_status(tenant_id, status)
            if count > 0:
                status_distribution[status] = count
        
        # 获取处理状态分布
        proc_status_distribution = {}
        files = await self.file_repo.find_by_tenant(tenant_id, limit=1000)  # 限制数量避免内存问题
        for file in files:
            proc_status = file.proc_status
            proc_status_distribution[proc_status] = proc_status_distribution.get(proc_status, 0) + 1
        
        # 获取可见性分布
        visibility_distribution = {}
        for file in files:
            visibility = file.visibility
            visibility_distribution[visibility] = visibility_distribution.get(visibility, 0) + 1
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "file_type_distribution": file_type_distribution,
            "status_distribution": status_distribution,
            "proc_status_distribution": proc_status_distribution,
            "visibility_distribution": visibility_distribution
        }
    
    async def get_daily_upload_stats(self, tenant_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取每日上传统计"""
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "status": {"$ne": Status.ARCHIVED.value},
                    "created_at": {
                        "$gte": get_current_timestamp().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1},
                    "total_size": {"$sum": "$file_size"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        return await File.aggregate(pipeline).to_list()


# 创建全局实例
file_repository = FileRepository()
file_log_repository = FileLogRepository()
file_statistics_service = FileStatisticsService(file_repository)