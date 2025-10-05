# foxmask/file/repositories/file_repository.py
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from beanie import PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from foxmask.core.logger import logger
from foxmask.file.models import (
    FileMetadata, FileChunk, UploadTask, UploadTaskFile, 
    FileStatus, FileVisibility, FileType, ChunkStatus, UploadTaskType
)
from foxmask.file.dto import FileResponseDTO, UploadTaskResponseDTO
from foxmask.utils.helpers import get_current_time

class FileRepository:
    """文件元数据仓库"""
    
    def __init__(self, motor_client: AsyncIOMotorClient):
        self.motor_client = motor_client
    
    async def get_file_by_id(self, file_id: UUID) -> Optional[FileMetadata]:
        """根据ID获取文件"""
        try:
            return await FileMetadata.get(file_id)
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {e}")
            return None
    
    async def get_files_by_ids(self, file_ids: List[UUID]) -> List[FileMetadata]:
        """根据ID列表获取文件"""
        try:
            files = await FileMetadata.find({"_id": {"$in": file_ids}}).to_list()
            return files
        except Exception as e:
            logger.error(f"Error getting files by IDs: {e}")
            return []
    
    async def create_file(self, file_data: Dict[str, Any]) -> FileMetadata:
        """创建文件记录"""
        try:
            file = FileMetadata(**file_data)
            await file.insert()
            logger.info(f"Created file record: {file.id}")
            return file
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            raise
    
    async def update_file(self, file_id: UUID, update_data: Dict[str, Any]) -> Optional[FileMetadata]:
        """更新文件记录"""
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                return None
            
            # 更新字段
            for key, value in update_data.items():
                if hasattr(file, key):
                    setattr(file, key, value)
            
            file.updated_at = get_current_time()
            await file.save()
            logger.info(f"Updated file: {file_id}")
            return file
        except Exception as e:
            logger.error(f"Error updating file {file_id}: {e}")
            return None
    
    async def delete_file(self, file_id: UUID) -> bool:
        """删除文件记录"""
        try:
            file = await self.get_file_by_id(file_id)
            if file:
                await file.delete()
                logger.info(f"Deleted file: {file_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    async def list_files(
        self, 
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        page: int = 1, 
        page_size: int = 10,
        status: Optional[FileStatus] = None,
        visibility: Optional[FileVisibility] = None,
        file_type: Optional[FileType] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[List[FileMetadata], int]:
        """列出文件"""
        try:
            query = {}
            
            if user_id:
                query["uploaded_by"] = user_id
            if tenant_id:
                query["tenant_id"] = tenant_id
            if status:
                query["status"] = status
            if visibility:
                query["visibility"] = visibility
            if file_type:
                query["file_type"] = file_type
            if tags:
                query["tags"] = {"$in": tags}
            
            skip = (page - 1) * page_size
            files = await FileMetadata.find(
                query, 
                skip=skip, 
                limit=page_size,
                sort=[("created_at", -1)]
            ).to_list()
            
            total_count = await FileMetadata.find(query).count()
            
            return files, total_count
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return [], 0
    
    async def get_user_files_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户文件统计"""
        try:
            # 文件总数
            total_files = await FileMetadata.find({"uploaded_by": user_id}).count()
            
            # 按状态统计
            status_stats = {}
            for status in FileStatus:
                count = await FileMetadata.find({
                    "uploaded_by": user_id, 
                    "status": status
                }).count()
                status_stats[status.value] = count
            
            # 按类型统计
            type_stats = {}
            for file_type in FileType:
                count = await FileMetadata.find({
                    "uploaded_by": user_id, 
                    "file_type": file_type
                }).count()
                type_stats[file_type.value] = count
            
            # 总存储大小
            pipeline = [
                {"$match": {"uploaded_by": user_id}},
                {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
            ]
            result = await FileMetadata.aggregate(pipeline).to_list()
            total_size = result[0]["total_size"] if result else 0
            
            return {
                "total_files": total_files,
                "status_stats": status_stats,
                "type_stats": type_stats,
                "total_size": total_size
            }
        except Exception as e:
            logger.error(f"Error getting user files stats: {e}")
            return {
                "total_files": 0,
                "status_stats": {},
                "type_stats": {},
                "total_size": 0
            }

class FileChunkRepository:
    """文件分块仓库"""
    
    def __init__(self, motor_client: AsyncIOMotorClient):
        self.motor_client = motor_client
    
    async def get_chunk(self, file_id: UUID, chunk_number: int) -> Optional[FileChunk]:
        """获取文件分块"""
        try:
            return await FileChunk.find_one({
                "file_id": file_id, 
                "chunk_number": chunk_number
            })
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_number} for file {file_id}: {e}")
            return None
    
    async def get_file_chunks(self, file_id: UUID, page: int = 1, page_size: int = 50) -> List[FileChunk]:
        """获取文件的所有分块"""
        try:
            skip = (page - 1) * page_size
            chunks = await FileChunk.find(
                {"file_id": file_id},
                skip=skip,
                limit=page_size,
                sort=[("chunk_number", 1)]
            ).to_list()
            return chunks
        except Exception as e:
            logger.error(f"Error getting chunks for file {file_id}: {e}")
            return []
    
    async def count_file_chunks(self, file_id: UUID) -> int:
        """统计文件分块数量"""
        try:
            return await FileChunk.find({"file_id": file_id}).count()
        except Exception as e:
            logger.error(f"Error counting chunks for file {file_id}: {e}")
            return 0
    
    async def create_chunks(self, chunks: List[FileChunk]) -> bool:
        """创建多个分块记录"""
        try:
            await FileChunk.insert_many(chunks)
            logger.info(f"Created {len(chunks)} chunk records")
            return True
        except Exception as e:
            logger.error(f"Error creating chunks: {e}")
            return False
    
    async def update_chunk(self, chunk: FileChunk) -> bool:
        """更新分块记录"""
        try:
            chunk.updated_at = get_current_time()
            await chunk.save()
            return True
        except Exception as e:
            logger.error(f"Error updating chunk {chunk.id}: {e}")
            return False
    
    async def delete_file_chunks(self, file_id: UUID) -> bool:
        """删除文件的所有分块"""
        try:
            await FileChunk.find({"file_id": file_id}).delete()
            logger.info(f"Deleted chunks for file {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks for file {file_id}: {e}")
            return False
    
    async def count_chunks_by_status(self, file_id: UUID, status: ChunkStatus) -> int:
        """按状态统计分块数量"""
        try:
            return await FileChunk.find({
                "file_id": file_id,
                "status": status
            }).count()
        except Exception as e:
            logger.error(f"Error counting chunks by status for file {file_id}: {e}")
            return 0
    
    async def get_upload_progress(self, file_id: UUID) -> Dict[str, Any]:
        """获取文件上传进度"""
        try:
            file = await FileMetadata.get(file_id)
            if not file:
                return {}
            
            uploaded_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
            verified_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.VERIFIED)
            total_chunks = file.total_chunks
            
            progress_percentage = 0.0
            if total_chunks > 0:
                progress_percentage = (uploaded_chunks / total_chunks) * 100
            
            return {
                "file_id": str(file_id),
                "filename": file.filename,
                "status": file.status,
                "uploaded_chunks": uploaded_chunks,
                "total_chunks": total_chunks,
                "progress_percentage": round(progress_percentage, 2)
            }
        except Exception as e:
            logger.error(f"Error getting upload progress for file {file_id}: {e}")
            return {}

class UploadTaskRepository:
    """上传任务仓库"""
    
    def __init__(self, motor_client: AsyncIOMotorClient):
        self.motor_client = motor_client
    
    async def get_task_by_id(self, task_id: UUID) -> Optional[UploadTask]:
        """根据ID获取任务"""
        try:
            return await UploadTask.get(task_id)
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def create_task(self, task_data: Dict[str, Any]) -> UploadTask:
        """创建上传任务"""
        try:
            task = UploadTask(**task_data)
            await task.insert()
            logger.info(f"Created upload task: {task.id}")
            return task
        except Exception as e:
            logger.error(f"Error creating upload task: {e}")
            raise
    
    async def update_task(self, task_id: UUID, update_data: Dict[str, Any]) -> Optional[UploadTask]:
        """更新上传任务"""
        try:
            task = await self.get_task_by_id(task_id)
            if not task:
                return None
            
            for key, value in update_data.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            task.updated_at = get_current_time()
            await task.save()
            return task
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: UUID) -> bool:
        """删除上传任务"""
        try:
            task = await self.get_task_by_id(task_id)
            if task:
                await task.delete()
                logger.info(f"Deleted upload task: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
    
    async def get_user_tasks(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 20,
        status: Optional[FileStatus] = None
    ) -> Tuple[List[UploadTask], int]:
        """获取用户的上传任务"""
        try:
            query = {"uploaded_by": user_id}
            if status:
                query["status"] = status
            
            skip = (page - 1) * page_size
            tasks = await UploadTask.find(
                query,
                skip=skip,
                limit=page_size,
                sort=[("created_at", -1)]
            ).to_list()
            
            total_count = await UploadTask.find(query).count()
            
            return tasks, total_count
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return [], 0
    
    async def add_file_to_task(self, task_id: UUID, file_id: UUID, file_path: str, file_order: int = 0) -> bool:
        """向任务添加文件"""
        try:
            task_file = UploadTaskFile(
                task_id=task_id,
                file_id=file_id,
                file_path=file_path,
                file_order=file_order
            )
            await task_file.insert()
            
            # 更新任务的文件ID列表
            task = await self.get_task_by_id(task_id)
            if task and file_id not in task.file_ids:
                task.file_ids.append(file_id)
                await task.save()
            
            return True
        except Exception as e:
            logger.error(f"Error adding file to task: {e}")
            return False
    
    async def get_task_files(self, task_id: UUID) -> List[UploadTaskFile]:
        """获取任务的文件列表"""
        try:
            task_files = await UploadTaskFile.find({"task_id": task_id}).to_list()
            return task_files
        except Exception as e:
            logger.error(f"Error getting task files for task {task_id}: {e}")
            return []
    
    async def update_task_file_progress(
        self, 
        task_file_id: UUID, 
        progress: float, 
        status: FileStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """更新任务文件进度"""
        try:
            task_file = await UploadTaskFile.get(task_file_id)
            if task_file:
                task_file.progress = progress
                task_file.status = status
                task_file.error_message = error_message
                task_file.updated_at = get_current_time()
                await task_file.save()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating task file progress: {e}")
            return False

# 存储库管理器
class RepositoryManager:
    """存储库管理器"""
    
    def __init__(self, motor_client: AsyncIOMotorClient):
        self.motor_client = motor_client
        self.file_repo = FileRepository(motor_client)
        self.chunk_repo = FileChunkRepository(motor_client)
        self.task_repo = UploadTaskRepository(motor_client)
    
    async def init_indexes(self):
        """初始化数据库索引"""
        try:
            await FileMetadata.get_motor_collection().create_index("uploaded_by")
            await FileMetadata.get_motor_collection().create_index("tenant_id")
            await FileMetadata.get_motor_collection().create_index("status")
            await FileMetadata.get_motor_collection().create_index("file_type")
            await FileMetadata.get_motor_collection().create_index("created_at")
            
            await FileChunk.get_motor_collection().create_index("file_id")
            await FileChunk.get_motor_collection().create_index("upload_id")
            await FileChunk.get_motor_collection().create_index("chunk_number")
            await FileChunk.get_motor_collection().create_index("status")
            
            await UploadTask.get_motor_collection().create_index("uploaded_by")
            await UploadTask.get_motor_collection().create_index("tenant_id")
            await UploadTask.get_motor_collection().create_index("status")
            await UploadTask.get_motor_collection().create_index("created_at")
            
            await UploadTaskFile.get_motor_collection().create_index("task_id")
            await UploadTaskFile.get_motor_collection().create_index("file_id")
            await UploadTaskFile.get_motor_collection().create_index("status")
            
            logger.info("Database indexes initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database indexes: {e}")
            raise