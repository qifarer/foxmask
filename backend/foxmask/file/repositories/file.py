# -*- coding: utf-8 -*-
# foxmask/file/repositories/file_repository.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# File repository for database operations

# 标准库导入
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any, Tuple

# 第三方库导入
from bson import ObjectId

# 本地模块导入
from foxmask.core.logger import logger
from foxmask.file.models import File, FileChunk, FileStatus, ChunkStatus, FileVisibility, FileType
from foxmask.utils.helpers import get_current_time


class FileRepository:
    """
    文件数据仓库类
    处理文件相关的数据库操作
    """
    
    def __init__(self):
        """初始化线程池执行器"""
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _run_in_thread(self, func, *args, **kwargs) -> Any:
        """
        在线程池中运行同步函数
        
        Args:
            func: 要执行的同步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def get_file_by_id(self, file_id: str) -> Optional[File]:
        """
        通过ID获取文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[File]: 文件对象或None
        """
        try:
            if not ObjectId.is_valid(file_id):
                logger.warning(f"Invalid file ID format: {file_id}")
                return None
            return await File.get(file_id)
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {e}")
            raise
    
    async def get_file_by_file_id(self, file_id: str) -> Optional[File]:
        """
        通过文件ID获取文件
        
        Args:
            file_id: 文件标识符
            
        Returns:
            Optional[File]: 文件对象或None
        """
        try:
            return await File.find_one(File.file_id == file_id)
        except Exception as e:
            logger.error(f"Error getting file by file_id {file_id}: {e}")
            raise
    
    async def save_file(self, file: File) -> File:
        """
        保存文件
        
        Args:
            file: 文件对象
            
        Returns:
            File: 保存后的文件对象
        """
        try:
            await file.save()
            logger.debug(f"File saved successfully: {file.filename}")
            return file
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise
    
    async def create_file(self, file_data: Dict[str, Any]) -> File:
        """
        创建新文件
        
        Args:
            file_data: 文件数据字典
            
        Returns:
            File: 新创建的文件对象
        """
        try:
            file = File(**file_data)
            await file.insert()
            logger.info(f"File created successfully: {file.filename}")
            return file
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            file = await self.get_file_by_id(file_id)
            if file:
                await file.delete()
                logger.info(f"File deleted successfully: {file_id}")
                return True
            logger.warning(f"File not found for deletion: {file_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            raise
    
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
    ) -> Tuple[List[File], int]:
        """
        分页列出文件
        
        Args:
            user_id: 用户ID筛选
            tenant_id: 租户ID筛选
            page: 页码
            page_size: 每页大小
            status: 状态筛选
            visibility: 可见性筛选
            file_type: 文件类型筛选
            tags: 标签筛选
            
        Returns:
            Tuple[List[File], int]: 文件列表和总数量
        """
        try:
            query = File.find()
            
            # 构建查询条件
            if user_id:
                query = query.find(File.uploaded_by == user_id)
            
            if tenant_id:
                query = query.find(File.tenant_id == tenant_id)
            
            if status:
                query = query.find(File.status == status)
            
            if visibility:
                query = query.find(File.visibility == visibility)
            
            if file_type:
                query = query.find(File.file_type == file_type)
            
            if tags:
                query = query.find(File.tags.in_(tags))
            
            # 排序和分页
            query = query.sort(-File.created_at)
            
            total_count = await query.count()
            files = await query.skip((page - 1) * page_size).limit(page_size).to_list()
            
            logger.debug(f"Listed {len(files)} files, total: {total_count}")
            return files, total_count
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def update_file(self, file_id: str, update_data: Dict[str, Any]) -> Optional[File]:
        """
        更新文件信息
        
        Args:
            file_id: 文件ID
            update_data: 更新数据
            
        Returns:
            Optional[File]: 更新后的文件对象或None
        """
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                logger.warning(f"File not found for update: {file_id}")
                return None
            
            # 更新字段
            for field, value in update_data.items():
                if hasattr(file, field):
                    setattr(file, field, value)
            
            file.updated_at = get_current_time()
            await file.save()
            
            logger.info(f"File updated successfully: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error updating file {file_id}: {e}")
            raise
    
    async def update_file_status(self, file_id: str, status: FileStatus) -> Optional[File]:
        """
        更新文件状态
        
        Args:
            file_id: 文件ID
            status: 新状态
            
        Returns:
            Optional[File]: 更新后的文件对象或None
        """
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                logger.warning(f"File not found for status update: {file_id}")
                return None
            
            file.status = status
            file.updated_at = get_current_time()
            await file.save()
            
            logger.info(f"File status updated to {status}: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error updating file status {file_id}: {e}")
            raise
    
    async def increment_download_count(self, file_id: str) -> Optional[File]:
        """
        增加文件下载计数
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[File]: 更新后的文件对象或None
        """
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                logger.warning(f"File not found for download count increment: {file_id}")
                return None
            
            file.download_count += 1
            file.last_downloaded_at = get_current_time()
            file.updated_at = get_current_time()
            await file.save()
            
            logger.info(f"Download count incremented for file: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error incrementing download count {file_id}: {e}")
            raise
    
    async def increment_view_count(self, file_id: str) -> Optional[File]:
        """
        增加文件查看计数
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[File]: 更新后的文件对象或None
        """
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                logger.warning(f"File not found for view count increment: {file_id}")
                return None
            
            file.view_count += 1
            file.last_viewed_at = get_current_time()
            file.updated_at = get_current_time()
            await file.save()
            
            logger.info(f"View count incremented for file: {file_id}")
            return file
            
        except Exception as e:
            logger.error(f"Error incrementing view count {file_id}: {e}")
            raise
    
    async def get_user_files_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户文件统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        try:
            # 总文件数
            total_files = await File.find(File.uploaded_by == user_id).count()
            
            # 总文件大小
            total_size_pipeline = [
                {"$match": {"uploaded_by": user_id}},
                {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
            ]
            total_size_result = await File.aggregate(total_size_pipeline).to_list()
            total_size = total_size_result[0]["total_size"] if total_size_result else 0
            
            # 状态统计
            status_counts = {}
            for status in FileStatus:
                count = await File.find(
                    File.uploaded_by == user_id,
                    File.status == status
                ).count()
                status_counts[status.value] = count
            
            # 类型统计
            type_counts = {}
            for file_type in FileType:
                count = await File.find(
                    File.uploaded_by == user_id,
                    File.file_type == file_type
                ).count()
                type_counts[file_type.value] = count
            
            stats = {
                "total_files": total_files,
                "total_size": total_size,
                "status_counts": status_counts,
                "type_counts": type_counts
            }
            
            logger.debug(f"Retrieved file stats for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user files stats {user_id}: {e}")
            raise

    async def create_chunk(self, chunk_data: Dict[str, Any]) -> FileChunk:
        """
        创建文件分片
        
        Args:
            chunk_data: 分片数据
            
        Returns:
            FileChunk: 新创建的分片对象
        """
        try:
            chunk = FileChunk(**chunk_data)
            await chunk.insert()
            logger.debug(f"Chunk created for file {chunk_data.get('file_id')}")
            return chunk
        except Exception as e:
            logger.error(f"Error creating chunk: {e}")
            raise
    
    async def create_chunks(self, chunks: List[FileChunk]) -> None:
        """
        批量创建文件分片
        
        Args:
            chunks: 分片对象列表
        """
        try:
            await FileChunk.bulk_insert(chunks)
            logger.info(f"Bulk created {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Error creating chunks: {e}")
            raise
    
    async def get_chunk(self, file_id: str, chunk_number: int) -> Optional[FileChunk]:
        """
        获取指定分片
        
        Args:
            file_id: 文件ID
            chunk_number: 分片编号
            
        Returns:
            Optional[FileChunk]: 分片对象或None
        """
        try:
            return await FileChunk.find_one(
                FileChunk.file_id == file_id,
                FileChunk.chunk_number == chunk_number
            )
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_number} for file {file_id}: {e}")
            raise
    
    async def get_file_chunks(self, file_id: str, page: int = 1, page_size: int = 50) -> List[FileChunk]:
        """
        获取文件的所有分片
        
        Args:
            file_id: 文件ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            List[FileChunk]: 分片列表
        """
        try:
            chunks = await FileChunk.find(FileChunk.file_id == file_id)\
                .sort(FileChunk.chunk_number)\
                .skip((page - 1) * page_size)\
                .limit(page_size)\
                .to_list()
            logger.debug(f"Retrieved {len(chunks)} chunks for file {file_id}")
            return chunks
        except Exception as e:
            logger.error(f"Error getting chunks for file {file_id}: {e}")
            raise
    
    async def update_chunk(self, chunk: FileChunk) -> FileChunk:
        """
        更新分片信息
        
        Args:
            chunk: 分片对象
            
        Returns:
            FileChunk: 更新后的分片对象
        """
        try:
            await chunk.save()
            logger.debug(f"Chunk updated: {chunk.chunk_number}")
            return chunk
        except Exception as e:
            logger.error(f"Error updating chunk {chunk.chunk_number}: {e}")
            raise
    
    async def update_chunk_status(
        self, 
        file_id: str, 
        chunk_number: int, 
        status: ChunkStatus, 
        error_message: Optional[str] = None
    ) -> Optional[FileChunk]:
        """
        更新分片状态
        
        Args:
            file_id: 文件ID
            chunk_number: 分片编号
            status: 新状态
            error_message: 错误信息
            
        Returns:
            Optional[FileChunk]: 更新后的分片对象或None
        """
        try:
            chunk = await self.get_chunk(file_id, chunk_number)
            if not chunk:
                logger.warning(f"Chunk not found: file {file_id}, chunk {chunk_number}")
                return None
            
            chunk.status = status
            if error_message:
                chunk.error_message = error_message
            
            # 更新时间戳
            if status == ChunkStatus.UPLOADED:
                chunk.uploaded_at = get_current_time()
            elif status == ChunkStatus.VERIFIED:
                chunk.verified_at = get_current_time()
            
            await chunk.save()
            logger.info(f"Chunk status updated to {status}: file {file_id}, chunk {chunk_number}")
            return chunk
            
        except Exception as e:
            logger.error(f"Error updating chunk status {file_id}:{chunk_number}: {e}")
            raise
    
    async def delete_file_chunks(self, file_id: str) -> int:
        """
        删除文件的所有分片
        
        Args:
            file_id: 文件ID
            
        Returns:
            int: 删除的分片数量
        """
        try:
            result = await FileChunk.find(FileChunk.file_id == file_id).delete()
            logger.info(f"Deleted {result.deleted_count} chunks for file {file_id}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting chunks for file {file_id}: {e}")
            raise
    
    async def count_chunks_by_status(self, file_id: str, status: ChunkStatus) -> int:
        """
        统计指定状态的分片数量
        
        Args:
            file_id: 文件ID
            status: 分片状态
            
        Returns:
            int: 分片数量
        """
        try:
            count = await FileChunk.find(
                FileChunk.file_id == file_id,
                FileChunk.status == status
            ).count()
            logger.debug(f"Counted {count} chunks with status {status} for file {file_id}")
            return count
        except Exception as e:
            logger.error(f"Error counting chunks by status for file {file_id}: {e}")
            raise
    
    async def count_file_chunks(self, file_id: str) -> int:
        """
        统计文件的分片总数
        
        Args:
            file_id: 文件ID
            
        Returns:
            int: 分片总数
        """
        try:
            count = await FileChunk.find(FileChunk.file_id == file_id).count()
            logger.debug(f"Total chunks for file {file_id}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting chunks for file {file_id}: {e}")
            raise
    
    async def get_upload_progress(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件上传进度
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict[str, Any]: 上传进度信息
        """
        try:
            file = await self.get_file_by_id(file_id)
            if not file:
                logger.warning(f"File not found for upload progress: {file_id}")
                return {}
            
            uploaded_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.UPLOADED)
            verified_chunks = await self.count_chunks_by_status(file_id, ChunkStatus.VERIFIED)
            
            progress_percentage = 0.0
            if file.total_chunks > 0:
                progress_percentage = (uploaded_chunks / file.total_chunks) * 100
            
            progress_info = {
                "file_id": file_id,
                "filename": file.filename,
                "status": file.status,
                "uploaded_chunks": uploaded_chunks,
                "verified_chunks": verified_chunks,
                "total_chunks": file.total_chunks,
                "progress_percentage": progress_percentage
            }
            
            logger.info(f"Upload progress for file {file_id}: {progress_info}")
            return progress_info
            
        except Exception as e:
            logger.error(f"Error getting upload progress for file {file_id}: {e}")
            raise


# 全局文件仓库实例
file_repository = FileRepository()