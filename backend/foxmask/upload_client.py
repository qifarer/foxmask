# upload_client.py
import asyncio
import aiohttp
import json
import os, re
import hashlib
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import mimetypes
from tqdm import tqdm
import time


class UploadTaskType(str, Enum):
    """上传任务类型"""
    SINGLE_FILE = "SINGLE_FILE"
    MULTI_FILES = "MULTI_FILES" 
    DIRECTORY = "DIRECTORY"
    BATCH_DIRECTORIES = "BATCH_DIRECTORIES"

class UploadSourceType(str, Enum):
    """上传源类型"""
    SINGLE_FILE = "SINGLE_FILE"
    MULTIPLE_FILES = "MULTIPLE_FILES" 
    SINGLE_DIRECTORY = "SINGLE_DIRECTORY"
    MULTIPLE_DIRECTORIES = "MULTIPLE_DIRECTORIES"

class UploadStrategy(str, Enum):
    """上传策略"""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    STREAMING = "STREAMING"

class FileType(str, Enum):
    """文件类型枚举"""
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    ARCHIVE = "ARCHIVE"
    CODE = "CODE"
    DATA = "DATA"
    OTHER = "OTHER"


@dataclass
class UploadConfig:
    """上传配置"""
    graphql_endpoint: str = "http://localhost:8888/graphql"
    auth_token: str = "your-auth-token-here"
    default_chunk_size: int = 5 * 1024 * 1024  # 5MB
    max_parallel_uploads: int = 3
    timeout: int = 300


class UploadClient:
    """完整的文件上传客户端 - 纯GraphQL版本"""
    
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
        
        # 定义文件类型映射
        document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.ppt', '.pptx', '.xls', '.xlsx'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.php', '.rb', '.go'}
        data_extensions = {'.json', '.xml', '.csv', '.sql', '.db', '.sqlite'}
        
        if extension in document_extensions:
            return FileType.DOCUMENT
        elif extension in image_extensions:
            return FileType.IMAGE
        elif extension in video_extensions:
            return FileType.VIDEO
        elif extension in audio_extensions:
            return FileType.AUDIO
        elif extension in archive_extensions:
            return FileType.ARCHIVE
        elif extension in code_extensions:
            return FileType.CODE
        elif extension in data_extensions:
            return FileType.DATA
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
                "original_path": file_path,  # 修正字段名
                "filename": Path(file_path).name,
                "storage_path": storage_path,  # 修正字段名
                "file_size": file_size,  # 修正字段名
                "file_type": file_type,
                "content_type": content_type or "application/octet-stream",
                "extension": Path(file_path).suffix.lower(),
                "checksum_md5": checksum_md5,
                "checksum_sha256": checksum_sha256,
                "extracted_metadata": {  # 修正字段名
                    "created_time": file_stat.st_ctime,
                    "modified_time": file_stat.st_mtime,
                }
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
        """发现文件（排除隐藏文件/目录，以及数字结尾文件）"""
        file_infos = []
        number_suffix_pattern = re.compile(r'\d+$')

        for source_path in source_paths:
            if source_type in [UploadSourceType.SINGLE_FILE, UploadSourceType.MULTIPLE_FILES]:
                # 单文件或多文件上传
                filename = os.path.basename(source_path)
                # 跳过隐藏文件或数字结尾文件
                if filename.startswith('.') or number_suffix_pattern.search(os.path.splitext(filename)[0]):
                    continue

                file_info = await self._analyze_file(source_path, source_path, preserve_structure, base_upload_path)
                if file_info and self._filter_file(file_info, file_type_filters, max_file_size):
                    file_infos.append(file_info)
            else:
                # 目录上传
                for root, dirs, files in os.walk(source_path):
                    # 排除隐藏目录（以 "." 开头）
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                    for filename in files:
                        # 排除隐藏文件或数字结尾文件
                        if filename.startswith('.') or number_suffix_pattern.search(os.path.splitext(filename)[0]):
                            continue

                        file_path = os.path.join(root, filename)
                        file_info = await self._analyze_file(file_path, source_path, preserve_structure, base_upload_path)
                        if file_info and self._filter_file(file_info, file_type_filters, max_file_size):
                            file_infos.append(file_info)

        return file_infos
    
    def _filter_file(self, file_info: Dict[str, Any], file_type_filters: List[FileType], max_file_size: int) -> bool:
        """文件过滤"""
        if file_type_filters and file_info["file_type"] not in file_type_filters:
            return False
        
        if max_file_size and file_info["file_size"] > max_file_size:
            print(f"文件超过大小限制 {file_info['filename']}: {file_info['file_size']} > {max_file_size}")
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
        """
        start_time = time.time()
        base_upload_path = 'file'
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
                upload_results['file_results']
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
        print(file_infos)
        total_size = sum(f["file_size"] for f in file_infos)
        print(f"📊 发现 {len(file_infos)} 个文件, 总大小: {total_size / 1024 / 1024:.2f} MB")
        
        # GraphQL初始化Mutation - 修正为正确的Mutation名称和字段
        init_mutation = """
        mutation InitializeUpload($input: InitializeUploadInput!) {
        upload {
            initializeUpload(input: $input) {
                success
                errors {
                    message
                    code
                    field
                }
                data {
                    uid
                    title
                    totalFiles
                    totalSize
                    files {
                      uid
                      tenantId
                      masterId
                      filename
                      originalPath
                      fileSize
                    }
                }
            }
        } }
        """
        
        # 修正输入变量结构
        init_variables = {
            "input": {
                "title": title,
                "desc": description or f"上传: {title}",
                "sourceType": source_type.name,  # 使用枚举名称
                "sourcePaths": source_paths,
                "uploadStrategy": upload_strategy.name,  # 使用枚举名称
                "maxParallelUploads": max_parallel_uploads,
                "chunkSize": chunk_size,
                "preserveStructure": preserve_structure,
                "baseUploadPath": base_upload_path,
                "autoExtractMetadata": True,
                "fileTypeFilters": [f.name for f in file_type_filters],  # 使用枚举名称
                "maxFileSize": max_file_size,
                "files": [
                    {
                        "originalPath": f["original_path"],
                        "filename": f["filename"],
                        "fileSize": f["file_size"],
                        "fileType": f["file_type"].name,  # 使用枚举名称
                        "contentType": f["content_type"],
                        "extension": f["extension"],
                        "chunkSize": chunk_size
                    } for f in file_infos
                ]
            }
        }
        
        print("🔄 初始化上传任务...")
        
        try:
            result = await self.execute_graphql(init_mutation, init_variables)
            print("===================execute_graphql 444444======================")
            print(str(result))
            init_response = result["upload"]["initializeUpload"]
            
            if not init_response["success"]:
                errors = init_response.get("errors", [])
                error_msg = "; ".join([f"{e.get('field', '')}: {e['message']}" for e in errors])
                raise Exception(f"初始化失败: {error_msg}")
            print("===================execute_graphql 555555======================")
            data = init_response["data"]
            return {
                "task_id": data["uid"],
                "total_files": data["totalFiles"],
                "total_size": data["totalSize"],
                "chunk_size": chunk_size,
                "file_infos": data["files"]
            }
        except Exception as e:
            print(f"❌ GraphQL请求失败: {e}")
            raise
    
    async def _upload_files(
        self, 
        init_result: Dict[str, Any], 
        max_parallel_uploads: int
    ) -> Dict[str, Any]:
        """上传文件分块 - 使用GraphQL"""
        print("🔄 开始上传文件...")
        
        success_count = 0
        failed_count = 0
        file_results = {}
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_parallel_uploads)
        print(f"_upload_files:=====init_result={str(init_result)}")
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
            upload_tasks.append((file_info["filename"], task))
        
        # 显示总体进度
        with tqdm(total=len(upload_tasks), desc="总体进度", unit="file") as pbar:
            for filename, task in upload_tasks:
                try:
                    result = await task
                    file_results[filename] = result
                    if result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    file_results[filename] = {"success": False, "error": str(e)}
                    failed_count += 1
                pbar.update(1)
        
        return {
            "success": success_count, 
            "failed": failed_count,
            "file_results": file_results
        }
    
    async def _upload_single_file(
        self, 
        task_id: str, 
        file_info: Dict[str, Any], 
        chunk_size: int, 
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """上传单个文件 - 使用GraphQL"""
        async with semaphore:
            try:
                file_path = file_info["originalPath"]
                file_size = file_info["fileSize"]
                filename = file_info["filename"]
                
                # 为每个文件生成唯一的file_id
                file_id = file_info['uid']
                
                total_chunks = (file_size + chunk_size - 1) // chunk_size
                
                print(f"📤 开始上传文件: {filename} (大小: {file_size} bytes, 分块: {total_chunks})")
                
                # 文件进度条
                with tqdm(total=file_size, unit='B', unit_scale=True, 
                         desc=filename[:20], leave=False) as pbar:
                    
                    with open(file_path, 'rb') as f:
                        for chunk_num in range(total_chunks):
                            chunk_data = f.read(chunk_size)
                            start_byte = chunk_num * chunk_size
                            end_byte = start_byte + len(chunk_data) - 1
                            is_final_chunk = (chunk_num == total_chunks - 1)
                            
                            # 计算校验和
                            checksum_md5 = hashlib.md5(chunk_data).hexdigest()
                            checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()
                            
                            # 使用GraphQL上传分块
                            success = await self._upload_chunk_graphql(
                                task_id=task_id,
                                file_id=file_id,
                                chunk_number=chunk_num + 1,
                                chunk_data=chunk_data,
                                chunk_size=len(chunk_data),
                                start_byte=start_byte,
                                end_byte=end_byte,
                                is_final_chunk=is_final_chunk,
                                checksum_md5=checksum_md5,
                                checksum_sha256=checksum_sha256
                            )
                            
                            if not success:
                                return {"success": False, "error": f"分块 {chunk_num + 1} 上传失败"}
                            
                            pbar.update(len(chunk_data))
                
                # 完成文件上传
                complete_success = await self._complete_file_upload(
                    task_id=task_id,
                    file_id=file_id,
                    checksum_md5=file_info.get("checksum_md5"),
                    checksum_sha256=file_info.get("checksum_sha256")
                )
                
                if not complete_success:
                    return {"success": False, "error": "文件完成操作失败"}
                
                return {"success": True, "file_id": file_id}
                
            except Exception as e:
                print(f"文件上传失败 {file_info['filename']}: {e}")
                return {"success": False, "error": str(e)}
    
    async def _upload_chunk_graphql(
        self,
        task_id: str,
        file_id: str,
        chunk_number: int,
        chunk_data: bytes,
        chunk_size: int,
        start_byte: int,
        end_byte: int,
        is_final_chunk: bool,
        checksum_md5: str,
        checksum_sha256: str
    ) -> bool:
        """通过GraphQL上传单个分块"""
        try:
            print("===============_upload_chunk_graphql==============")
            # 将二进制数据编码为base64
            chunk_data_base64 = base64.b64encode(chunk_data).decode('utf-8')
            
            upload_chunk_mutation = """
            mutation UploadChunk($input: UploadChunkInput!) {
            upload {
                uploadChunk(input: $input) {
                    success
                    errors {
                        message
                        code
                        field
                    }
                    data {
                        uid
                        chunkNumber
                    }
                }
            }
            }
            """

            chunk_variables = {
                "input": {
                    "taskId": task_id,
                    "fileId": file_id,
                    "chunkNumber": chunk_number,
                    "chunkData": chunk_data_base64,
                    "chunkSize": chunk_size,
                    "startByte": start_byte,
                    "endByte": end_byte,
                    "isFinalChunk": is_final_chunk,
                    "minioBucket": "uploads",  # 默认存储桶
                    "minioObjectName": f"{file_id}/chunk_{chunk_number:06d}",
                    "checksumMd5": checksum_md5,
                    "checksumSha256": checksum_sha256,
                    "maxRetries": 3
                }
            }
            print(f"chunk_variables====:task_id={str(task_id)},fileId={file_id}")
            result = await self.execute_graphql(upload_chunk_mutation, chunk_variables)
            print(f"result====:{str(result)}")
            upload_response = result["upload"]["uploadChunk"]
            
            if not upload_response["success"]:
                errors = upload_response.get("errors", [])
                error_msg = "; ".join([e["message"] for e in errors])
                print(f"分块上传失败: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            print(f"分块上传失败: {e}")
            return False
    
    async def _complete_file_upload(
        self,
        task_id: str,
        file_id: str,
        checksum_md5: str = None,
        checksum_sha256: str = None
    ) -> bool:
        """完成单个文件上传"""
        try:
            complete_mutation = """
            mutation CompleteUpload($input: CompleteUploadInput!) {
            upload {
                completeUpload(input: $input) {
                    success
                    errors {
                        message
                        code
                        field
                    }
                    data {
                        uid
                        filename
                        procStatus
                    }
                }
            }
            }
            """
            
            complete_variables = {
                "input": {
                    "taskId": task_id,
                    "fileId": file_id,
                    "checksumMd5": checksum_md5,
                    "checksumSha256": checksum_sha256
                }
            }
            
            result = await self.execute_graphql(complete_mutation, complete_variables)
            complete_response = result["upload"]["completeUpload"]
            
            if not complete_response["success"]: 
                errors = complete_response.get("errors", [])
                error_msg = "; ".join([e["message"] for e in errors])
                print(f"文件完成失败: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            print(f"文件完成失败: {e}")
            return False
    
    async def _complete_upload_task(self, task_id: str, file_results: Dict[str, Any]) -> Dict[str, Any]:
        """完成上传任务 - 这里主要是收集结果，实际文件完成已在 _complete_file_upload 中处理"""
        print("✅ 所有文件上传完成")
        return {
            "success": True,
            "message": "所有文件上传完成",
            "task_id": task_id,
            "file_results": file_results
        }
    
    async def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        query = """
        query GetUploadTask($taskId: String!) {
        upload{
            getUploadTask(taskId: $taskId) {
                success
                errors {
                    message
                    code
                    field
                }
                data {
                    uid
                    title
                    totalFiles
                    totalSize
                    completedFiles
                    failedFiles
                    uploadedSize
                }
            }
          }
        }
        """
        
        try:
            result = await self.execute_graphql(query, {"taskId": task_id})
            print(str(result))
            task_response = result["upload"]["getUploadTask"]
            if not task_response["success"]:
                return {"success": False, "error": "获取任务进度失败"}
            
            return {"success": True, "data": task_response["data"]}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def main():
    """主函数 - 演示各种上传场景"""
    access_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlcnRfaDM3ZXlwIiwidHlwIjoiSldUIn0.eyJvd25lciI6ImFkbWluIiwibmFtZSI6ImZveG1hc2siLCJjcmVhdGVkVGltZSI6IiIsInVwZGF0ZWRUaW1lIjoiIiwiZGVsZXRlZFRpbWUiOiIiLCJpZCI6ImFkbWluL2ZveG1hc2siLCJ0eXBlIjoiYXBwbGljYXRpb24iLCJwYXNzd29yZCI6IiIsInBhc3N3b3JkU2FsdCI6IiIsInBhc3N3b3JkVHlwZSI6IiIsImRpc3BsYXlOYW1lIjoiIiwiZmlyc3ROYW1lIjoiIiwibGFzdE5hbWUiOiIiLCJhdmF0YXIiOiIiLCJhdmF0YXJUeXBlIjoiIiwicGVybWFuZW50QXZhdGFyIjoiIiwiZW1haWwiOiIiLCJlbWFpbFZlcmlmaWVkIjpmYWxzZSwicGhvbmUiOiIiLCJjb3VudHJ5Q29kZSI6IiIsInJlZ2lvbiI6IiIsImxvY2F0aW9uIjoiIiwiYWRkcmVzcyI6W10sImFmZmlsaWF0aW9uIjoiIiwidGl0bGUiOiIiLCJpZENhcmRUeXBlIjoiIiwiaWRDYXJkIjoiIiwiaG9tZXBhZ2UiOiIiLCJiaW8iOiIiLCJsYW5ndWFnZSI6IiIsImdlbmRlciI6IiIsImJpcnRoZGF5IjoiIiwiZWR1Y2F0aW9uIjoiIiwic2NvcmUiOjAsImthcm1hIjowLCJyYW5raW5nIjowLCJpc0RlZmF1bHRBdmF0YXIiOmZhbHNlLCJpc09ubGluZSI6ZmFsc2UsImlzQWRtaW4iOmZhbHNlLCJpc0ZvcmJpZGRlbiI6ZmFsc2UsImlzRGVsZXRlZCI6ZmFsc2UsInNpZ251cEFwcGxpY2F0aW9uIjoiIiwiaGFzaCI6IiIsInByZUhhc2giOiIiLCJhY2Nlc3NLZXkiOiIiLCJhY2Nlc3NTZWNyZXQiOiIiLCJnaXRodWIiOiIiLCJnb29nbGUiOiIiLCJxcSI6IiIsIndlY2hhdCI6IiIsImZhY2Vib29rIjoiIiwiZGluZ3RhbGsiOiIiLCJ3ZWlibyI6IiIsImdpdGVlIjoiIiwibGlua2VkaW4iOiIiLCJ3ZWNvbSI6IiIsImxhcmsiOiIiLCJnaXRsYWIiOiIiLCJjcmVhdGVkSXAiOiIiLCJsYXN0U2lnbmluVGltZSI6IiIsImxhc3RTaWduaW5JcCI6IiIsInByZWZlcnJlZE1mYVR5cGUiOiIiLCJyZWNvdmVyeUNvZGVzIjpudWxsLCJ0b3RwU2VjcmV0IjoiIiwibWZhUGhvbmVFbmFibGVkIjpmYWxzZSwibWZhRW1haWxFbmFibGVkIjpmYWxzZSwibGRhcCI6IiIsInByb3BlcnRpZXMiOnt9LCJyb2xlcyI6W10sInBlcm1pc3Npb25zIjpbXSwiZ3JvdXBzIjpbXSwibGFzdFNpZ25pbldyb25nVGltZSI6IiIsInNpZ25pbldyb25nVGltZXMiOjAsIm1hbmFnZWRBY2NvdW50cyI6bnVsbCwidG9rZW5UeXBlIjoiYWNjZXNzLXRva2VuIiwidGFnIjoiIiwiYXpwIjoiMjVjN2JiZTJmZWVkM2YzNzhkMjEiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwMDAiLCJzdWIiOiJhZG1pbi9mb3htYXNrIiwiYXVkIjpbIjI1YzdiYmUyZmVlZDNmMzc4ZDIxIl0sImV4cCI6MTc2MDE5MDI4OCwibmJmIjoxNzU5NTg1NDg4LCJpYXQiOjE3NTk1ODU0ODgsImp0aSI6ImFkbWluLzhiYTgxMGM1LWNjOTYtNDRlZC05NWQwLTdiMTI3YWZlOWMxNyJ9.q8--YR6xZvbNqKaK0v9URIvJ2mzZBO845Mu5-eKxjoakZR10VJCTtPZE1-EcSygRKMGC1NV7cA83zIQX33CtY8pJJifSr5s-4WrQiPtebX3sTAXhqlGxpggjyKsbqCXnztH2ofMyPyY0r-jZiUljHqx0R7GoZrjk3DXThFwJlR4WBhz5grDuBZC3tSezlqIwcyUfjyGAq7RP6qIBuya9SNAA1yXqP_qqHYXLwl-tvwkWVc9_4OtxBK-_fDuiwE-VvoSoYlJ5rmkMr65b523mpFYyUaBl8PKlvK4QRKrQhfZb4xYEf2iMncj0LZoqXaqto5DV5PE2YPr2isgytlB3BawxexGYL5grLhZ054lofI48mfUhL6OHzv4_WAiMJX8ef9F92H2sdMgS8i13Cd_ZUpjx9q2fF5VVwUOpdLRaQ-wSYNvwi_KhZKFQThXdC1EbRVespAkbUKPeDW7hqUjo_DSib4rRbjNfq7CvOyRzS7YFcEYGVPMMsKQlRj4DI0dhym0oLL8mgxbWXSH0Z8F1e30BaX56D1aHJbSfrK_LCUhbzvCYWyq24k3AZ6qr4ghiFXtI6bTIpKRwp4GLabG_GV1fxvZXhRabPfOU-82oynbWM-SyLb_3px3oBLfAWUDiVTkGEspuEvV9eLcfEKs2doHHDvhQNFZSagmVQW2AiP4"
    # 配置客户端
    config = UploadConfig(
        graphql_endpoint="http://localhost:8888/graphql",
        auth_token=access_token,
        max_parallel_uploads=2
    )
    
    async with UploadClient(config) as client:
        print("=" * 50)
        print("📁 文件上传客户端演示 - 纯GraphQL版本")
        print("=" * 50)
            
        # 测试文件
        filenames = [
            "/Users/luoqi/Downloads/开发服务合同.pdf",
            "/Users/luoqi/Downloads/Add_edit direct deposit – confirmation.pdf",
        ]
        
        # 场景1: 上传多个文件
        '''
        print("\n1. 📚 多个文件上传")
        result1 = await client.upload(
            source_paths=filenames,
            title="测试多文件上传",
            description="上传多个文本文件测试",
            upload_strategy=UploadStrategy.PARALLEL,
        )
        print(f"结果: {json.dumps(result1, indent=2, ensure_ascii=False)}")
        '''
        
        # 场景2: 上传目录
        directories = ["/Users/luoqi/Downloads/高中-数学",
                       "/Users/luoqi/Downloads/大学",
                       ]
        print("\n2. 📁 目录上传")
        result2 = await client.upload(
            source_paths=directories,
            title="测试目录上传",
            description="上传整个目录测试",
            preserve_structure=True,
            base_upload_path="test_uploads"
        )
        print(f"结果: {json.dumps(result2, indent=2, ensure_ascii=False)}")
       
        
        # 监控进度示例
        if result2.get('task_id'):
            print("\n3. 📊 监控上传进度")
            for i in range(3):  # 监控3次
                progress = await client.get_task_progress(result2['task_id'])
                print(str(progress))
                if progress['success']:
                    data = progress['data']
                    percentage = (data['completedFiles'] / data['totalFiles']) * 100 if data['totalFiles'] > 0 else 0
                    print(f"进度 {i+1}: {percentage:.1f}% ({data['completedFiles']}/{data['totalFiles']})")
                else:
                    print(f"进度 {i+1}: 获取失败 - {progress['error']}")
                await asyncio.sleep(1)
        


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())