# optimized_upload_client.py
import asyncio
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from unified_upload_client import UnifiedUploadClient, UploadConfig


class OptimizedUploadClient:
    """优化后的上传客户端 - 统一初始化接口"""
    
    def __init__(self, base_client: UnifiedUploadClient):
        self.client = base_client
    
    async def upload_directory_optimized(self, directory_path: str, title: str, **kwargs) -> Dict[str, Any]:
        """
        优化后的目录上传流程 - 统一初始化
        """
        print(f"开始优化上传流程: {directory_path}")
        
        # 阶段1: 统一初始化任务和文件信息
        init_result = await self._phase1_unified_init(directory_path, title, **kwargs)
        
        print(f"阶段1完成: 任务 {init_result['task_id']}, 文件数 {init_result['total_files']}")
        
        # 阶段2: 上传文件分块
        upload_results = await self._phase2_upload_chunks(init_result, **kwargs)
        
        print(f"阶段2完成: 成功 {upload_results['success']}, 失败 {upload_results['failed']}")
        
        # 阶段3: 完成任务
        complete_result = await self._phase3_complete_task(init_result['task_id'], **kwargs)
        
        print(f"阶段3完成: {complete_result['message']}")
        
        return {
            "task_id": init_result['task_id'],
            "total_files": init_result['total_files'],
            "success_files": upload_results["success"],
            "failed_files": upload_results["failed"],
            "complete_result": complete_result
        }
    
    async def _phase1_unified_init(self, directory_path: str, title: str, **kwargs) -> Dict[str, Any]:
        """阶段1: 统一初始化任务和文件信息"""
        # 发现并分析文件
        file_infos = await self._discover_and_analyze_files(directory_path, **kwargs)
        
        if not file_infos:
            raise Exception("未发现可上传的文件")
        
        # 统一初始化Mutation
        init_mutation = """
        mutation InitUploadTask($input: UploadTaskInitInput!) {
            initUploadTask(input: $input) {
                success
                message
                task_id
                data {
                    task {
                        id
                        chunkSize
                    }
                    totalFiles
                    totalSize
                    totalChunks
                }
            }
        }
        """
        
        init_variables = {
            "input": {
                "taskType": "BATCH_UPLOAD",
                "sourceType": "SINGLE_DIRECTORY",
                "title": title,
                "desc": kwargs.get("desc", f"上传目录: {directory_path}"),
                "uploadStrategy": kwargs.get("upload_strategy", "PARALLEL"),
                "maxParallelUploads": kwargs.get("max_parallel_uploads", 5),
                "chunkSize": kwargs.get("chunk_size", 10 * 1024 * 1024),
                "preserveStructure": kwargs.get("preserve_structure", True),
                "baseUploadPath": kwargs.get("base_upload_path"),
                "fileTypeFilters": kwargs.get("file_type_filters", []),
                "files": file_infos
            }
        }
        
        init_result = await self.client.execute_graphql(init_mutation, init_variables)
        if not init_result["initUploadTask"]["success"]:
            raise Exception(f"统一初始化失败: {init_result['initUploadTask']['message']}")
        
        return {
            "task_id": init_result["initUploadTask"]["task_id"],
            "total_files": init_result["initUploadTask"]["data"]["totalFiles"],
            "total_size": init_result["initUploadTask"]["data"]["totalSize"],
            "total_chunks": init_result["initUploadTask"]["data"]["totalChunks"],
            "chunk_size": init_result["initUploadTask"]["data"]["task"]["chunkSize"],
            "file_infos": file_infos
        }
    
    async def _discover_and_analyze_files(self, directory_path: str, **kwargs) -> List[Dict[str, Any]]:
        """发现并分析文件"""
        file_infos = []
        preserve_structure = kwargs.get("preserve_structure", True)
        base_upload_path = kwargs.get("base_upload_path")
        
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # 文件类型过滤
                if not self._filter_file(file_path, kwargs.get("file_type_filters")):
                    continue
                
                # 文件大小过滤
                file_size = os.path.getsize(file_path)
                max_file_size = kwargs.get("max_file_size")
                if max_file_size and file_size > max_file_size:
                    continue
                
                # 计算存储路径
                if preserve_structure:
                    relative_path = os.path.relpath(file_path, directory_path)
                    storage_path = os.path.join(base_upload_path, relative_path) if base_upload_path else relative_path
                else:
                    storage_path = filename
                
                # 分析文件信息
                file_info = await self._analyze_file(file_path, storage_path)
                if file_info:
                    file_infos.append(file_info)
        
        return file_infos
    
    def _filter_file(self, file_path: str, file_type_filters: List[str]) -> bool:
        """文件类型过滤"""
        if not file_type_filters:
            return True
        
        file_extension = Path(file_path).suffix.lower()
        # 这里可以实现文件类型过滤逻辑
        return True
    
    async def _analyze_file(self, file_path: str, storage_path: str) -> Dict[str, Any]:
        """分析文件信息"""
        try:
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # 计算校验和（可选）
            checksum_md5 = None
            checksum_sha256 = None
            
            if file_size < 100 * 1024 * 1024:  # 只对小文件计算校验和
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    checksum_md5 = hashlib.md5(file_content).hexdigest()
                    checksum_sha256 = hashlib.sha256(file_content).hexdigest()
            
            # 检测文件类型
            file_type = self._detect_file_type(file_path)
            
            # 获取MIME类型
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_path)
            
            return {
                "filename": Path(file_path).name,
                "originalPath": file_path,
                "storagePath": storage_path,
                "fileSize": file_size,
                "fileType": file_type.value,
                "contentType": content_type or "application/octet-stream",
                "extension": Path(file_path).suffix.lower(),
                "checksumMd5": checksum_md5,
                "checksumSha256": checksum_sha256,
                "extractedMetadata": {
                    "createdTime": file_stat.st_ctime,
                    "modifiedTime": file_stat.st_mtime
                },
                "relativePath": os.path.relpath(file_path, os.path.dirname(file_path))
            }
        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return None
    
    def _detect_file_type(self, file_path: str):
        """检测文件类型"""
        from foxmask.file.models.base import FileType
        
        extension = Path(file_path).suffix.lower()
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg'}
        document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
        
        if extension in image_extensions:
            return FileType.IMAGE
        elif extension in video_extensions:
            return FileType.VIDEO
        elif extension in audio_extensions:
            return FileType.AUDIO
        elif extension in document_extensions:
            return FileType.DOCUMENT
        else:
            return FileType.OTHER
    
    async def _phase2_upload_chunks(self, init_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """阶段2: 上传文件分块"""
        success_count = 0
        failed_count = 0
        
        max_parallel = kwargs.get("max_parallel_uploads", 5)
        semaphore = asyncio.Semaphore(max_parallel)
        
        upload_tasks = []
        for file_info in init_result["file_infos"]:
            task = asyncio.create_task(
                self._upload_single_file(init_result["task_id"], file_info, init_result["chunk_size"], semaphore)
            )
            upload_tasks.append(task)
        
        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception) or not result:
                failed_count += 1
            else:
                success_count += 1
        
        return {"success": success_count, "failed": failed_count}
    
    async def _upload_single_file(self, task_id: str, file_info: Dict[str, Any], chunk_size: int, semaphore: asyncio.Semaphore) -> bool:
        """上传单个文件"""
        async with semaphore:
            try:
                file_path = file_info["originalPath"]
                file_size = file_info["fileSize"]
                
                print(f"开始上传文件: {file_info['filename']}")
                
                # 这里需要从服务端获取文件的file_id
                # 暂时使用文件名作为标识
                file_id = file_info["filename"]  # 实际应从初始化响应中获取
                
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                
                with open(file_path, 'rb') as f:
                    for chunk_num in range(total_chunks):
                        chunk_data = f.read(chunk_size)
                        is_final_chunk = (chunk_num == total_chunks - 1)
                        
                        checksum_md5 = hashlib.md5(chunk_data).hexdigest()
                        checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()
                        
                        success = await self._upload_single_chunk(
                            task_id=task_id,
                            file_id=file_id,
                            chunk_number=chunk_num + 1,
                            chunk_data=chunk_data,
                            is_final_chunk=is_final_chunk,
                            checksum_md5=checksum_md5,
                            checksum_sha256=checksum_sha256
                        )
                        
                        if not success:
                            return False
                
                print(f"文件上传完成: {file_info['filename']}")
                return True
                
            except Exception as e:
                print(f"文件上传失败 {file_info['filename']}: {e}")
                return False
    
    async def _upload_single_chunk(self, **chunk_info) -> bool:
        """上传单个分块"""
        try:
            result = await self.client.upload_chunk_rest(chunk_info)
            return result.get("success", False)
        except Exception as e:
            print(f"分块上传失败: {e}")
            return False
    
    async def _phase3_complete_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """阶段3: 完成任务"""
        complete_mutation = """
        mutation CompleteUploadTask($input: UploadTaskCompleteInput!) {
            completeUploadTask(input: $input) {
                success
                message
                completedFiles
                failedFiles
                totalFiles
            }
        }
        """
        
        complete_variables = {
            "input": {
                "taskId": task_id,
                "forceComplete": kwargs.get("force_complete", False)
            }
        }
        
        result = await self.client.execute_graphql(complete_mutation, complete_variables)
        return result["completeUploadTask"]


# 使用示例
async def main():
    config = UploadConfig(auth_token="your-token")
    
    async with UnifiedUploadClient(config) as base_client:
        optimized_client = OptimizedUploadClient(base_client)
        
        # 使用优化后的统一初始化接口
        result = await optimized_client.upload_directory_optimized(
            directory_path="/path/to/upload",
            title="项目文档上传",
            upload_strategy="PARALLEL",
            preserve_structure=True,
            base_upload_path="projects/2024",
            max_parallel_uploads=3
        )
        
        print(f"上传完成: {result}")

if __name__ == "__main__":
    asyncio.run(main())