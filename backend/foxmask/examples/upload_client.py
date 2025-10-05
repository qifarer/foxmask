# upload_client.py
import asyncio
import aiohttp
import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import mimetypes
from tqdm import tqdm
import time


class UploadSourceType(str, Enum):
    SINGLE_FILE = "SINGLE_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES"
    SINGLE_DIRECTORY = "SINGLE_DIRECTORY"
    MULTIPLE_DIRECTORIES = "MULTIPLE_DIRECTORIES"


class UploadStrategy(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


class FileType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"
    PDF = "PDF"
    TEXT = "TEXT"
    OTHER = "OTHER"


@dataclass
class UploadConfig:
    """上传配置"""
    graphql_endpoint: str = "http://localhost:8888/graphql"
    rest_endpoint: str = "http://localhost:8888/api/upload/chunk"
    auth_token: str = "your-auth-token-here"
    default_chunk_size: int = 5 * 1024 * 1024  # 5MB
    max_parallel_uploads: int = 3
    timeout: int = 300


class UploadClient:
    """完整的文件上传客户端"""
    
    def __init__(self, config: UploadConfig):
        self.config = config
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.config.auth_token}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行GraphQL查询"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        async with self.session.post(
            self.config.graphql_endpoint,
            json=payload
        ) as response:
            result = await response.json()
            if "errors" in result:
                raise Exception(f"GraphQL错误: {result['errors']}")
            return result["data"]
    
    async def upload_chunk_rest(self, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """通过REST API上传分块"""
        form_data = aiohttp.FormData()
        
        for key, value in chunk_data.items():
            if key == "chunk_data" and isinstance(value, bytes):
                form_data.add_field('chunk_data', value, filename='chunk.bin')
            else:
                form_data.add_field(key, str(value))
        
        async with self.session.post(
            self.config.rest_endpoint,
            data=form_data
        ) as response:
            return await response.json()
    
    def _determine_source_type(self, source_paths: List[str]) -> UploadSourceType:
        """确定源类型"""
        if len(source_paths) == 1:
            if os.path.isfile(source_paths[0]):
                return UploadSourceType.SINGLE_FILE
            elif os.path.isdir(source_paths[0]):
                return UploadSourceType.SINGLE_DIRECTORY
        else:
            if all(os.path.isfile(path) for path in source_paths):
                return UploadSourceType.MULTIPLE_FILES
            elif all(os.path.isdir(path) for path in source_paths):
                return UploadSourceType.MULTIPLE_DIRECTORIES
            else:
                return UploadSourceType.MULTIPLE_FILES
        
        raise ValueError("无法确定源类型")
    
    def _validate_source_paths(self, source_paths: List[str], source_type: UploadSourceType):
        """验证源路径"""
        for path in source_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"路径不存在: {path}")
            
            if source_type in [UploadSourceType.SINGLE_FILE, UploadSourceType.MULTIPLE_FILES]:
                if not os.path.isfile(path):
                    raise ValueError(f"路径不是文件: {path}")
            else:
                if not os.path.isdir(path):
                    raise ValueError(f"路径不是目录: {path}")
    
    def _detect_file_type(self, file_path: str) -> FileType:
        """检测文件类型"""
        extension = Path(file_path).suffix.lower()
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg'}
        document_extensions = {'.doc', '.docx', '.txt', '.rtf', '.odt'}
        
        if extension in image_extensions:
            return FileType.IMAGE
        elif extension in video_extensions:
            return FileType.VIDEO
        elif extension in audio_extensions:
            return FileType.AUDIO
        elif extension in document_extensions:
            return FileType.DOCUMENT
        elif extension == '.pdf':
            return FileType.PDF
        elif extension == '.txt':
            return FileType.TEXT
        else:
            return FileType.OTHER
    
    async def _analyze_file(
        self, 
        file_path: str, 
        base_path: str,
        preserve_structure: bool,
        base_upload_path: str
    ) -> Dict[str, Any]:
        """分析文件信息"""
        try:
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # 计算存储路径
            if preserve_structure and os.path.isdir(base_path):
                relative_path = os.path.relpath(file_path, base_path)
                storage_path = os.path.join(base_upload_path, relative_path) if base_upload_path else relative_path
            else:
                storage_path = os.path.basename(file_path)
            
            # 计算校验和（只对小文件）
            checksum_md5 = None
            checksum_sha256 = None
            
            if file_size < 10 * 1024 * 1024:  # 10MB以下计算校验和
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                        checksum_md5 = hashlib.md5(file_content).hexdigest()
                        checksum_sha256 = hashlib.sha256(file_content).hexdigest()
                except Exception:
                    pass  # 忽略校验和计算错误
            
            # 获取文件类型和MIME类型
            file_type = self._detect_file_type(file_path)
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
                    "modifiedTime": file_stat.st_mtime,
                },
                "relativePath": os.path.relpath(file_path, os.path.dirname(file_path)) if preserve_structure else None
            }
        except Exception as e:
            print(f"分析文件失败 {file_path}: {e}")
            return None
    
    async def _discover_files(
        self,
        source_paths: List[str],
        source_type: UploadSourceType,
        preserve_structure: bool,
        base_upload_path: str,
        file_type_filters: List[FileType],
        max_file_size: int
    ) -> List[Dict[str, Any]]:
        """发现文件"""
        file_infos = []
        
        for source_path in source_paths:
            if source_type in [UploadSourceType.SINGLE_FILE, UploadSourceType.MULTIPLE_FILES]:
                # 文件上传
                file_info = await self._analyze_file(source_path, source_path, preserve_structure, base_upload_path)
                if file_info and self._filter_file(file_info, file_type_filters, max_file_size):
                    file_infos.append(file_info)
            else:
                # 目录上传
                for root, dirs, files in os.walk(source_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        file_info = await self._analyze_file(file_path, source_path, preserve_structure, base_upload_path)
                        if file_info and self._filter_file(file_info, file_type_filters, max_file_size):
                            file_infos.append(file_info)
        
        return file_infos
    
    def _filter_file(self, file_info: Dict[str, Any], file_type_filters: List[FileType], max_file_size: int) -> bool:
        """文件过滤"""
        if file_type_filters and file_info["fileType"] not in [f.value for f in file_type_filters]:
            return False
        
        if max_file_size and file_info["fileSize"] > max_file_size:
            print(f"文件超过大小限制 {file_info['filename']}: {file_info['fileSize']} > {max_file_size}")
            return False
        
        return True
    
    async def upload(
        self,
        source_paths: Union[str, List[str]],
        title: str,
        description: str = None,
        upload_strategy: UploadStrategy = UploadStrategy.PARALLEL,
        chunk_size: int = None,
        preserve_structure: bool = True,
        base_upload_path: str = None,
        file_type_filters: List[FileType] = None,
        max_file_size: int = None,
        max_parallel_uploads: int = None
    ) -> Dict[str, Any]:
        """
        统一上传接口
        
        Args:
            source_paths: 源路径
            title: 任务标题
            description: 任务描述
            upload_strategy: 上传策略
            chunk_size: 分块大小
            preserve_structure: 是否保持目录结构
            base_upload_path: 基础上传路径
            file_type_filters: 文件类型过滤器
            max_file_size: 最大文件大小
            max_parallel_uploads: 最大并行上传数
        """
        start_time = time.time()
        
        try:
            # 标准化输入
            if isinstance(source_paths, str):
                source_paths = [source_paths]
            
            source_type = self._determine_source_type(source_paths)
            self._validate_source_paths(source_paths, source_type)
            
            # 使用默认值
            if chunk_size is None:
                chunk_size = self.config.default_chunk_size
            if max_parallel_uploads is None:
                max_parallel_uploads = self.config.max_parallel_uploads
            
            print(f"🚀 开始上传: {title}")
            print(f"📁 类型: {source_type.value}")
            print(f"📍 路径: {source_paths}")
            
            # 阶段1: 初始化任务
            init_result = await self._init_upload_task(
                source_paths=source_paths,
                source_type=source_type,
                title=title,
                description=description,
                upload_strategy=upload_strategy,
                chunk_size=chunk_size,
                preserve_structure=preserve_structure,
                base_upload_path=base_upload_path,
                file_type_filters=file_type_filters or [],
                max_file_size=max_file_size,
                max_parallel_uploads=max_parallel_uploads
            )
            
            print(f"✅ 初始化完成: {init_result['total_files']} 个文件")
            
            # 阶段2: 上传文件
            upload_results = await self._upload_files(
                init_result, 
                max_parallel_uploads
            )
            
            print(f"✅ 上传完成: 成功 {upload_results['success']}, 失败 {upload_results['failed']}")
            
            # 阶段3: 完成任务
            complete_result = await self._complete_upload_task(
                init_result['task_id'], 
                force_complete=upload_results['failed'] > 0
            )
            
            duration = time.time() - start_time
            
            return {
                "success": upload_results['failed'] == 0,
                "message": f"上传完成: 成功 {upload_results['success']}, 失败 {upload_results['failed']}",
                "task_id": init_result['task_id'],
                "total_files": init_result['total_files'],
                "success_files": upload_results["success"],
                "failed_files": upload_results["failed"],
                "total_size": init_result['total_size'],
                "duration": f"{duration:.2f}秒",
                "complete_result": complete_result
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "message": f"上传失败: {str(e)}",
                "duration": f"{duration:.2f}秒"
            }
    
    async def _init_upload_task(
        self,
        source_paths: List[str],
        source_type: UploadSourceType,
        title: str,
        description: str,
        upload_strategy: UploadStrategy,
        chunk_size: int,
        preserve_structure: bool,
        base_upload_path: str,
        file_type_filters: List[FileType],
        max_file_size: int,
        max_parallel_uploads: int
    ) -> Dict[str, Any]:
        """初始化上传任务"""
        # 发现文件
        file_infos = await self._discover_files(
            source_paths, source_type, preserve_structure, 
            base_upload_path, file_type_filters, max_file_size
        )
        
        if not file_infos:
            raise Exception("未发现可上传的文件")
        
        total_size = sum(f["fileSize"] for f in file_infos)
        print(f"📊 发现 {len(file_infos)} 个文件, 总大小: {total_size / 1024 / 1024:.2f} MB")
        
        # GraphQL初始化Mutation
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
                "sourceType": source_type.value,
                "title": title,
                "desc": description or f"上传: {title}",
                "uploadStrategy": upload_strategy.value,
                "maxParallelUploads": max_parallel_uploads,
                "chunkSize": chunk_size,
                "preserveStructure": preserve_structure,
                "baseUploadPath": base_upload_path,
                "autoExtractMetadata": True,
                "fileTypeFilters": [f.value for f in file_type_filters],
                "maxFileSize": max_file_size,
                "files": file_infos
            }
        }
        
        print("🔄 初始化上传任务...")
        result = await self.execute_graphql(init_mutation, init_variables)
        
        if not result["initUploadTask"]["success"]:
            raise Exception(f"初始化失败: {result['initUploadTask']['message']}")
        
        return {
            "task_id": result["initUploadTask"]["task_id"],
            "total_files": result["initUploadTask"]["data"]["totalFiles"],
            "total_size": result["initUploadTask"]["data"]["totalSize"],
            "chunk_size": result["initUploadTask"]["data"]["task"]["chunkSize"],
            "file_infos": file_infos
        }
    
    async def _upload_files(
        self, 
        init_result: Dict[str, Any], 
        max_parallel_uploads: int
    ) -> Dict[str, Any]:
        """上传文件分块"""
        print("🔄 开始上传文件...")
        
        success_count = 0
        failed_count = 0
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_parallel_uploads)
        
        # 创建上传任务
        upload_tasks = []
        for file_info in init_result["file_infos"]:
            task = asyncio.create_task(
                self._upload_single_file(
                    init_result["task_id"],
                    file_info,
                    init_result["chunk_size"],
                    semaphore
                )
            )
            upload_tasks.append(task)
        
        # 显示总体进度
        with tqdm(total=len(upload_tasks), desc="总体进度", unit="file") as pbar:
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception) or not result:
                    failed_count += 1
                else:
                    success_count += 1
                pbar.update(1)
        
        return {"success": success_count, "failed": failed_count}
    
    async def _upload_single_file(
        self, 
        task_id: str, 
        file_info: Dict[str, Any], 
        chunk_size: int, 
        semaphore: asyncio.Semaphore
    ) -> bool:
        """上传单个文件"""
        async with semaphore:
            try:
                file_path = file_info["originalPath"]
                file_size = file_info["fileSize"]
                file_id = file_info["filename"]  # 简化处理，使用文件名作为file_id
                
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                
                # 文件进度条
                with tqdm(total=file_size, unit='B', unit_scale=True, 
                         desc=file_info["filename"][:20], leave=False) as pbar:
                    
                    with open(file_path, 'rb') as f:
                        for chunk_num in range(total_chunks):
                            chunk_data = f.read(chunk_size)
                            is_final_chunk = (chunk_num == total_chunks - 1)
                            
                            # 计算校验和
                            checksum_md5 = hashlib.md5(chunk_data).hexdigest()
                            checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()
                            
                            # 上传分块
                            success = await self._upload_chunk(
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
                            
                            pbar.update(len(chunk_data))
                
                return True
                
            except Exception as e:
                print(f"文件上传失败 {file_info['filename']}: {e}")
                return False
    
    async def _upload_chunk(
        self,
        task_id: str,
        file_id: str,
        chunk_number: int,
        chunk_data: bytes,
        is_final_chunk: bool,
        checksum_md5: str,
        checksum_sha256: str
    ) -> bool:
        """上传单个分块"""
        try:
            chunk_info = {
                "task_id": task_id,
                "file_id": file_id,
                "chunk_number": chunk_number,
                "chunk_data": chunk_data,
                "is_final_chunk": is_final_chunk,
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256
            }
            
            result = await self.upload_chunk_rest(chunk_info)
            return result.get("success", False)
            
        except Exception as e:
            print(f"分块上传失败: {e}")
            return False
    
    async def _complete_upload_task(self, task_id: str, force_complete: bool = False) -> Dict[str, Any]:
        """完成上传任务"""
        print("🔄 完成任务...")
        
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
                "forceComplete": force_complete
            }
        }
        
        result = await self.execute_graphql(complete_mutation, complete_variables)
        return result["completeUploadTask"]
    
    async def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        query = """
        query GetUploadProgress($id: String!) {
            uploadTask(id: $id) {
                taskStatus
                totalFiles
                completedFiles
                failedFiles
                totalSize
                uploadedSize
                progressPercentage
            }
        }
        """
        
        result = await self.execute_graphql(query, {"id": task_id})
        return result["uploadTask"]


async def main():
    """主函数 - 演示各种上传场景"""
    
    # 配置客户端
    config = UploadConfig(
        graphql_endpoint="http://localhost:8000/graphql",
        rest_endpoint="http://localhost:8000/api/upload/chunk",
        auth_token="your-jwt-token-here",  # 替换为实际token
        max_parallel_uploads=2
    )
    
    async with UploadClient(config) as client:
        print("=" * 50)
        print("📁 文件上传客户端演示")
        print("=" * 50)
        
        # 创建测试文件（如果不存在）
        test_dir = "test_upload_files"
        os.makedirs(test_dir, exist_ok=True)
        
        # 创建一些测试文件
        test_files = [
            ("small_file.txt", "这是一个小文本文件"),
            ("medium_file.txt", "这是一个中等大小的文件\n" * 1000),
        ]
        
        for filename, content in test_files:
            filepath = os.path.join(test_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"创建测试文件: {filepath}")
        
        # 场景1: 上传单个文件
        print("\n1. 📄 单个文件上传")
        result1 = await client.upload(
            source_paths=os.path.join(test_dir, "small_file.txt"),
            title="测试单个文件上传",
            description="上传单个文本文件测试"
        )
        print(f"结果: {result1}")
        
        # 场景2: 上传多个文件
        print("\n2. 📚 多个文件上传")
        result2 = await client.upload(
            source_paths=[
                os.path.join(test_dir, "small_file.txt"),
                os.path.join(test_dir, "medium_file.txt")
            ],
            title="测试多文件上传",
            description="上传多个文本文件测试",
            upload_strategy=UploadStrategy.PARALLEL
        )
        print(f"结果: {result2}")
        
        # 场景3: 上传目录
        print("\n3. 📁 目录上传")
        result3 = await client.upload(
            source_paths=test_dir,
            title="测试目录上传",
            description="上传整个目录测试",
            preserve_structure=True,
            base_upload_path="test_uploads"
        )
        print(f"结果: {result3}")
        
        # 监控进度示例
        if result3.get('task_id'):
            print("\n4. 📊 监控上传进度")
            for i in range(3):  # 监控3次
                progress = await client.get_task_progress(result3['task_id'])
                print(f"进度 {i+1}: {progress['progressPercentage']:.1f}%")
                await asyncio.sleep(1)


async def quick_start():
    """快速开始示例"""
    config = UploadConfig(
        graphql_endpoint="http://localhost:8888/graphql",
        rest_endpoint="http://localhost:8888/api/upload/chunk",
        auth_token="your-token-here"
    )
    
    async with UploadClient(config) as client:
        # 最简单的上传示例
        result = await client.upload(
            source_paths="path/to/your/file.txt",  # 替换为实际文件路径
            title="我的第一个上传任务"
        )
        print("上传结果:", result)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
    
    # 或者运行快速开始
    # asyncio.run(quick_start())