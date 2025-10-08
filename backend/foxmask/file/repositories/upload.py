# foxmask/file/repositories/upload.py
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from foxmask.core.logger import logger
from foxmask.file.enums import FileTypeEnum, UploadProcStatusEnum
from foxmask.file.models.upload import UploadTask, UploadTaskFile, UploadTaskFileChunk


class UploadTaskRepository:
    """上传任务仓库"""
    
    def __init__(self):
        self.model = UploadTask
    
    # ==================== 基础CRUD操作 ====================
    
    async def create(self, task: UploadTask) -> UploadTask:
        """创建上传任务"""
        return await task.insert()
    
    async def get_by_id(self, task_id: str) -> Optional[UploadTask]:
        """根据ID获取上传任务"""
        return await self.model.find_one({"uid": task_id})
    
    async def update(self, task_id: str, update_data: Dict[str, Any]) -> Optional[UploadTask]:
        """更新上传任务"""
        task = await self.get_by_id(task_id)
        if task:
            # 处理DTO对象转换
            if hasattr(update_data, 'dict'):
                # 如果是Pydantic模型
                update_data = update_data.dict(exclude_unset=True)
            elif hasattr(update_data, '__dataclass_fields__'):
                # 如果是dataclass，手动转换
                from dataclasses import fields
                update_dict = {}
                for field in fields(update_data):
                    value = getattr(update_data, field.name)
                    if value is not None:
                        update_dict[field.name] = value
                update_data = update_dict
            
            # 更新字段
            for key, value in update_data.items():
                setattr(task, key, value)
            await task.save()
            return task
        return None
    
    async def delete(self, task_id: str) -> bool:
        """删除上传任务"""
        task = await self.get_by_id(task_id)
        if task:
            await task.delete()
            return True
        return False
    
    async def bulk_create(self, tasks: List[UploadTask]) -> List[UploadTask]:
        """批量创建上传任务"""
        return await self.model.insert_many(tasks)
    
    # ==================== 查询方法 ====================
    
    async def list(
        self,
        filters: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> Tuple[List[UploadTask], int]:
        """分页查询上传任务列表"""
        query = {}
        if filters:
            query.update(filters)
        
        # 构建查询
        find_query = self.model.find(query)
        
        # 排序
        if sort_by:
            if sort_order == "desc":
                find_query = find_query.sort(-getattr(self.model, sort_by))
            else:
                find_query = find_query.sort(getattr(self.model, sort_by))
        
        # 分页
        entities = await find_query.skip(skip).limit(limit).to_list()
        
        # 总数
        total_count = await self.model.find(query).count()
        
        return entities, total_count
    
    async def get_by_filters(
        self,
        tenant_id: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[UploadTask]:
        """根据过滤器获取上传任务"""
        skip = (page - 1) * page_size
        query = {"tenant_id": tenant_id}
        
        if filters:
            query.update(filters)
            
        return await self.model.find(query).skip(skip).limit(page_size).to_list()
    
    async def get_by_tenant_and_status(
        self, 
        tenant_id: str, 
        status: UploadProcStatusEnum,
        page: int = 1, 
        page_size: int = 20
    ) -> List[UploadTask]:
        """根据租户和状态获取上传任务"""
        return await self.get_by_filters(
            tenant_id=tenant_id,
            filters={"proc_status": status},
            page=page,
            page_size=page_size
        )
    
    # ==================== 业务方法 ====================
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: UploadProcStatusEnum,
        **updates
    ) -> Optional[UploadTask]:
        """更新上传任务状态"""
        update_data = {"proc_status": status}
        update_data.update(updates)
        return await self.update(task_id, update_data)
    
    async def increment_progress(
        self,
        task_id: str,
        uploaded_size: int = 0,
        completed_files: int = 0,
        failed_files: int = 0,
        processing_files: int = 0,
        discovered_files: int = 0
    ) -> Optional[UploadTask]:
        """增量更新上传任务进度"""
        task = await self.get_by_id(task_id)
        if task:
            update_data = {}
            if uploaded_size:
                update_data["uploaded_size"] = task.uploaded_size + uploaded_size
            if completed_files:
                update_data["completed_files"] = task.completed_files + completed_files
            if failed_files:
                update_data["failed_files"] = task.failed_files + failed_files
            if processing_files:
                update_data["processing_files"] = task.processing_files + processing_files
            if discovered_files:
                update_data["discovered_files"] = task.discovered_files + discovered_files
            
            return await self.update(task_id, update_data)
        return None
    
    async def get_active_tasks(self, tenant_id: str) -> List[UploadTask]:
        """获取活跃的上传任务"""
        return await self.get_by_filters(
            tenant_id=tenant_id,
            filters={
                "proc_status": {
                    "$in": [
                        UploadProcStatusEnum.PENDING, 
                        UploadProcStatusEnum.UPLOADING, 
                        UploadProcStatusEnum.PROCESSING
                    ]
                }
            }
        )
    
    async def cancel_upload_task(self, task_id: str) -> Optional[UploadTask]:
        """取消上传任务"""
        return await self.update_task_status(task_id, UploadProcStatusEnum.CANCELLED)
    
    async def update_discovery_progress(
        self,
        task_id: str,
        discovered_files: int = 0,
        total_files: int = 0,
        total_size: int = 0
    ) -> Optional[UploadTask]:
        """更新文件发现进度"""
        update_data = {}
        if discovered_files is not None:
            update_data["discovered_files"] = discovered_files
        if total_files is not None:
            update_data["total_files"] = total_files
        if total_size is not None:
            update_data["total_size"] = total_size
            
        return await self.update(task_id, update_data)
    
    # ==================== 统计方法 ====================
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """统计上传任务数量"""
        query = {}
        if filters:
            query.update(filters)
        return await self.model.find(query).count()
    
    async def get_task_stats(self, tenant_id: str, created_by: Optional[str] = None) -> Dict[str, Any]:
        """获取上传任务统计信息"""
        match_stage = {"tenant_id": tenant_id}
        if created_by:
            match_stage["created_by"] = created_by
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$proc_status",
                "count": {"$sum": 1},
                "total_size": {"$sum": "$total_size"},
                "total_files": {"$sum": "$total_files"}
            }}
        ]
        
        result = await self.model.aggregate(pipeline).to_list()
        return {item["_id"]: item for item in result}
    
    async def get_stats(self, tenant_id: str, created_by: Optional[str] = None) -> Dict[str, Any]:
        """获取上传统计信息"""
        # 统计任务数量
        total_tasks = await self.count({"tenant_id": tenant_id})
        active_tasks = await self.count({
            "tenant_id": tenant_id,
            "proc_status": {
                "$in": [UploadProcStatusEnum.PENDING, UploadProcStatusEnum.UPLOADING]
            }
        })
        completed_tasks = await self.count({
            "tenant_id": tenant_id,
            "proc_status": UploadProcStatusEnum.COMPLETED
        })
        failed_tasks = await self.count({
            "tenant_id": tenant_id,
            "proc_status": UploadProcStatusEnum.FAILED
        })
        
        # 计算总文件数和总大小
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {
                "_id": None,
                "total_files": {"$sum": "$total_files"},
                "total_size": {"$sum": "$total_size"},
                "uploaded_size": {"$sum": "$uploaded_size"}
            }}
        ]
        
        size_result = await self.model.aggregate(pipeline).to_list()
        total_files = size_result[0]["total_files"] if size_result else 0
        total_size = size_result[0]["total_size"] if size_result else 0
        uploaded_size = size_result[0]["uploaded_size"] if size_result else 0
        
        return {
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_files": total_files,
            "total_size": total_size,
            "uploaded_size": uploaded_size,
            "progress": (uploaded_size / total_size * 100) if total_size > 0 else 0
        }


class UploadTaskFileRepository:
    """上传任务文件仓库"""
    
    def __init__(self):
        self.model = UploadTaskFile
    
    # ==================== 基础CRUD操作 ====================
    
    async def create(self, file: UploadTaskFile) -> UploadTaskFile:
        """创建上传任务文件"""
        return await file.insert()
    
    async def get_by_id(self, file_id: str) -> Optional[UploadTaskFile]:
        """根据ID获取上传任务文件"""
        return await self.model.find_one({"uid": file_id})
    
    async def update(self, file_id: str, update_data: Dict[str, Any]) -> Optional[UploadTaskFile]:
        """更新上传任务文件"""
        file = await self.get_by_id(file_id)
        if file:
            for key, value in update_data.items():
                setattr(file, key, value)
            await file.save()
            return file
        return None
    
    async def delete(self, file_id: str) -> bool:
        """删除上传任务文件"""
        file = await self.get_by_id(file_id)
        if file:
            await file.delete()
            return True
        return False
    
    async def bulk_create(self, files: List[UploadTaskFile]) -> List[UploadTaskFile]:
        """批量创建上传任务文件"""
        if not files:
            return []
        try:
            result = await self.model.insert_many(files)
            # 返回带 id 的实体对象
            for entity, inserted_id in zip(files, result.inserted_ids):
                entity.id = inserted_id
            return files
        except Exception as e:
            logger.error(f"批量创建上传任务文件失败: {e}")
            raise
    
    # ==================== 查询方法 ====================
    
    async def list_by_task(
        self, 
        task_id: str,
        tenant_id: Optional[str] = None,
        proc_status: Optional[UploadProcStatusEnum] = None,
        proc_statuses: Optional[List[UploadProcStatusEnum]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[UploadTaskFile]:
        """根据任务ID获取上传任务文件"""
        skip = (page - 1) * page_size
        query = {"master_id": task_id}
        
        if tenant_id:
            query["tenant_id"] = tenant_id
        if proc_status:
            query["proc_status"] = proc_status
        if proc_statuses:
            query["proc_status"] = {"$in": proc_statuses}
        
        return await self.model.find(query).skip(skip).limit(page_size).to_list()
    
    async def list(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> Tuple[List[UploadTaskFile], int]:
        """分页查询上传任务文件列表"""
        # 构建查询
        find_query = self.model.find(filters)
        
        # 排序
        if sort_by:
            if sort_order == "desc":
                find_query = find_query.sort(-getattr(self.model, sort_by))
            else:
                find_query = find_query.sort(getattr(self.model, sort_by))
        
        # 分页
        entities = await find_query.skip(skip).limit(limit).to_list()
        
        # 总数
        total_count = await self.model.find(filters).count()
        
        return entities, total_count
    
    async def get_by_task_id(
        self, 
        task_id: str,
        filters: Dict[str, Any] = None,
        page: int = 1, 
        page_size: int = 50
    ) -> List[UploadTaskFile]:
        """根据任务ID获取上传任务文件"""
        skip = (page - 1) * page_size
        query = {"master_id": task_id}
        
        if filters:
            query.update(filters)
        
        return await self.model.find(query).skip(skip).limit(page_size).to_list()
    
    async def get_by_original_path(self, task_id: str, original_path: str) -> Optional[UploadTaskFile]:
        """根据原始路径获取上传任务文件"""
        return await self.model.find_one({
            "master_id": task_id,
            "original_path": original_path
        })
    
    # ==================== 业务方法 ====================
    
    async def update_file_progress(
        self,
        file_id: str,
        uploaded_chunks: int,
        current_chunk: int,
        progress: float,
        upload_speed: Optional[float] = None,
        estimated_time: Optional[float] = None
    ) -> Optional[UploadTaskFile]:
        """更新文件上传进度"""
        update_data = {
            "uploaded_chunks": uploaded_chunks,
            "current_chunk": current_chunk,
            "progress": progress
        }
        if upload_speed is not None:
            update_data["upload_speed"] = upload_speed
        if estimated_time is not None:
            update_data["estimated_time_remaining"] = estimated_time
            
        return await self.update(file_id, update_data)
    
    async def update_file_status(
        self,
        file_id: str,
        status: UploadProcStatusEnum,
        **updates
    ) -> Optional[UploadTaskFile]:
        """更新文件状态"""
        update_data = {"proc_status": status}
        update_data.update(updates)
        return await self.update(file_id, update_data)
    
    async def mark_file_completed(self, file_id: str) -> Optional[UploadTaskFile]:
        """标记文件完成"""
        return await self.update_file_status(
            file_id,
            UploadProcStatusEnum.COMPLETED,
            progress=100.0,
            upload_completed_at=datetime.now(timezone.utc)
        )
    
    async def mark_file_failed(self, file_id: str, error_info: Dict[str, Any]) -> Optional[UploadTaskFile]:
        """标记文件失败"""
        return await self.update_file_status(
            file_id,
            UploadProcStatusEnum.FAILED,
            error_info=error_info
        )
    
    async def get_files_by_status(self, task_id: str, status: UploadProcStatusEnum) -> List[UploadTaskFile]:
        """根据状态获取上传任务文件"""
        return await self.get_by_task_id(
            task_id=task_id,
            filters={"proc_status": status}
        )
    
    # ==================== 统计方法 ====================
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """统计上传任务文件数量"""
        query = {}
        if filters:
            query.update(filters)
        return await self.model.find(query).count()
    
    async def get_completed_files_count(self, task_id: str) -> int:
        """获取已完成文件数量"""
        return await self.count({
            "master_id": task_id,
            "proc_status": UploadProcStatusEnum.COMPLETED
        })
    
    async def get_failed_files_count(self, task_id: str) -> int:
        """获取失败文件数量"""
        return await self.count({
            "master_id": task_id,
            "proc_status": UploadProcStatusEnum.FAILED
        })
    
    async def get_stats_by_task(self, task_id: str) -> Dict[str, Any]:
        """获取任务的文件统计信息"""
        try:
            # 获取所有相关文件
            files = await self.model.find({"master_id": task_id}).to_list()
            
            stats = {
                "total_files": len(files),
                "completed_files": 0,
                "failed_files": 0,
                "processing_files": 0,
                "total_size": 0,
                "uploaded_size": 0
            }
            
            for file in files:
                stats["total_size"] += file.file_size
                
                # 计算已上传大小
                uploaded_file_size = file.file_size * (file.progress / 100)
                stats["uploaded_size"] += int(uploaded_file_size)
                
                # 根据状态统计
                if file.proc_status == UploadProcStatusEnum.COMPLETED:
                    stats["completed_files"] += 1
                elif file.proc_status == UploadProcStatusEnum.FAILED:
                    stats["failed_files"] += 1
                elif file.proc_status in [
                    UploadProcStatusEnum.PENDING, 
                    UploadProcStatusEnum.UPLOADING, 
                    UploadProcStatusEnum.PROCESSING
                ]:
                    stats["processing_files"] += 1
            
            logger.debug(f"任务 {task_id} 统计: {stats}")
            return stats
                
        except Exception as e:
            logger.error(f"获取任务 {task_id} 统计失败: {e}")
            return {
                "total_files": 0,
                "completed_files": 0,
                "failed_files": 0,
                "processing_files": 0,
                "total_size": 0,
                "uploaded_size": 0
            }


class UploadTaskFileChunkRepository:
    """上传任务文件分块仓库"""
    
    def __init__(self):
        self.model = UploadTaskFileChunk
    
    # ==================== 基础CRUD操作 ====================
    
    async def create(self, chunk: UploadTaskFileChunk) -> UploadTaskFileChunk:
        """创建文件分块"""
        return await chunk.insert()
    
    async def get_by_id(self, chunk_id: str) -> Optional[UploadTaskFileChunk]:
        """根据ID获取文件分块"""
        return await self.model.find_one({"uid": chunk_id})
    
    async def update(self, chunk_id: str, update_data: Dict[str, Any]) -> Optional[UploadTaskFileChunk]:
        """更新文件分块"""
        chunk = await self.get_by_id(chunk_id)
        if chunk:
            for key, value in update_data.items():
                setattr(chunk, key, value)
            await chunk.save()
            return chunk
        return None
    
    async def delete(self, chunk_id: str) -> bool:
        """删除文件分块"""
        chunk = await self.get_by_id(chunk_id)
        if chunk:
            await chunk.delete()
            return True
        return False
    
    async def bulk_create(self, chunks: List[UploadTaskFileChunk]) -> List[UploadTaskFileChunk]:
        """批量创建文件分块"""
        return await self.model.insert_many(chunks)
    
    # ==================== 查询方法 ====================
    
    async def get_by_file_and_number(
        self, 
        file_id: str, 
        chunk_number: int
    ) -> Optional[UploadTaskFileChunk]:
        """根据文件和分块编号获取文件分块"""
        return await self.model.find_one({
            "file_id": file_id,
            "chunk_number": chunk_number
        })
    
    async def list_by_file(self, file_id: str) -> List[UploadTaskFileChunk]:
        """根据文件ID获取文件分块列表"""
        return await self.model.find({"file_id": file_id}).sort("chunk_number").to_list()
    
    async def get_chunk(
        self, 
        file_id: str, 
        chunk_number: int
    ) -> Optional[UploadTaskFileChunk]:
        """获取特定文件分块"""
        return await self.model.find_one({
            "file_id": file_id,
            "chunk_number": chunk_number
        })
    
    async def get_pending_chunks(self, file_id: str, limit: int = 10) -> List[UploadTaskFileChunk]:
        """获取待处理的文件分块"""
        return await self.model.find({
            "file_id": file_id,
            "proc_status": UploadProcStatusEnum.PENDING
        }).sort("chunk_number").limit(limit).to_list()
    
    # ==================== 业务方法 ====================
    
    async def update_chunk_status(
        self,
        file_id: str,
        chunk_number: int,
        status: UploadProcStatusEnum,
        minio_etag: Optional[str] = None,
        checksum_md5: Optional[str] = None,
        checksum_sha256: Optional[str] = None
    ) -> Optional[UploadTaskFileChunk]:
        """更新文件分块状态"""
        chunk = await self.get_chunk(file_id, chunk_number)
        if chunk:
            update_data = {"proc_status": status}
            if minio_etag:
                update_data["minio_etag"] = minio_etag
            if checksum_md5:
                update_data["checksum_md5"] = checksum_md5
            if checksum_sha256:
                update_data["checksum_sha256"] = checksum_sha256
            if status == UploadProcStatusEnum.COMPLETED:
                update_data["uploaded_at"] = datetime.now(timezone.utc)
                
            return await self.update(chunk.uid, update_data)
        return None
    
    async def mark_chunk_completed(
        self,
        file_id: str,
        chunk_number: int,
        minio_etag: str,
        checksum_md5: str,
        checksum_sha256: str
    ) -> Optional[UploadTaskFileChunk]:
        """标记文件分块完成"""
        return await self.update_chunk_status(
            file_id,
            chunk_number,
            UploadProcStatusEnum.COMPLETED,
            minio_etag=minio_etag,
            checksum_md5=checksum_md5,
            checksum_sha256=checksum_sha256
        )
    
    # ==================== 统计方法 ====================
    
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """统计文件分块数量"""
        query = {}
        if filters:
            query.update(filters)
        return await self.model.find(query).count()
    
    async def count_by_file(self, file_id: str) -> int:
        """统计文件的分块数量"""
        return await self.count({"file_id": file_id})
    
    async def get_completed_chunks_count(self, file_id: str) -> int:
        """获取已完成分块数量"""
        return await self.count({
            "file_id": file_id,
            "proc_status": UploadProcStatusEnum.COMPLETED
        })
    
    async def get_failed_chunks_count(self, file_id: str) -> int:
        """获取失败分块数量"""
        return await self.count({
            "file_id": file_id,
            "proc_status": UploadProcStatusEnum.FAILED
        })