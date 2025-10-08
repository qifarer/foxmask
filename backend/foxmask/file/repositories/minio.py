# -*- coding: utf-8 -*-
# foxmask/file/repositories/minio_repository.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# MinIO repository for storage operations

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from foxmask.core.config import settings
from foxmask.core.exceptions import ExternalServiceError
from foxmask.core.logger import logger
from foxmask.utils.helpers import generate_uuid
from foxmask.utils.minio_client import minio_client


class MinIORepository:
    """MinIO存储仓库类 - 处理MinIO存储操作"""
    
    def __init__(self):
        """初始化MinIO客户端和线程池"""
        self.minio = minio_client
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _run_in_thread(self, func, *args, **kwargs) -> Any:
        """在线程池中运行同步MinIO操作"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """确保存储桶存在"""
        try:
            exists = await self._run_in_thread(self.minio.bucket_exists, bucket_name)
            if not exists:
                await self._run_in_thread(self.minio.make_bucket, bucket_name)
                logger.info(f"创建MinIO存储桶: {bucket_name}")
        except Exception as e:
            logger.error(f"确保存储桶存在失败 {bucket_name}: {e}")
            raise ExternalServiceError("MinIO", "ensure_bucket_exists", str(e))
    
    def _generate_object_name(self, file_id: str, chunk_number: int) -> str:
        """生成分块对象名称"""
        return f"{file_id}/chunk_{chunk_number:06d}"
    
    # ==================== 分块上传操作 ====================
    
    async def upload_chunk(
        self,
        bucket: str,
        object_name: str,
        chunk_data: bytes,
        chunk_size: int = None,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """上传文件分块"""
        try:
            logger.info(f"=== MINIO 上传 ===")
            logger.info(f"分块数据类型: {type(chunk_data)}")
            logger.info(f"分块数据大小: {len(chunk_data)} 字节")
            
            # 验证数据类型
            if not isinstance(chunk_data, bytes):
                logger.error(f"期望字节数据，实际得到 {type(chunk_data)}")
                return {
                    "success": False,
                    "error": f"期望字节数据，实际得到 {type(chunk_data)}"
                }
            
            # 确保存储桶存在
            await self._ensure_bucket_exists(bucket)
            
            # 使用同步方法上传
            result = await self._run_in_thread(
                self.minio.put_object,
                bucket,
                object_name,
                chunk_data,
                content_type
            )
            
            logger.info(f"上传结果: {result}")
            
            # 立即验证上传
            try:
                await self._run_in_thread(
                    self.minio.client.stat_object,
                    bucket,
                    object_name
                )
                logger.info("上传验证: 成功")
            except Exception as e:
                logger.error(f"上传验证失败: {e}")
                return {
                    "success": False,
                    "error": f"上传验证失败: {str(e)}"
                }
            
            return {
                "success": True,
                "etag": result.get("etag") if isinstance(result, dict) else "unknown"
            }
            
        except Exception as e:
            logger.error(f"MinIO上传失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_chunk(
        self,
        bucket: str,
        object_name: str
    ) -> bytes:
        """下载文件分块"""
        try:
            chunk_data = await self.minio.download_file_as_bytes(object_name, bucket)
            
            if chunk_data is None:
                raise ExternalServiceError("MinIO", "download_chunk", "下载分块失败")
            
            logger.info(f"分块下载成功: {object_name}, 大小: {len(chunk_data)}")
            return chunk_data
            
        except Exception as e:
            logger.error(f"MinIO分块下载失败 - 存储桶: {bucket}, 对象: {object_name}, 错误: {e}")
            raise ExternalServiceError("MinIO", "download_chunk", str(e))
    
    async def chunk_exists(
        self,
        bucket: str,
        object_name: str
    ) -> bool:
        """检查分块是否存在"""
        try:
            await self._run_in_thread(
                self.minio.stat_object,
                bucket,
                object_name
            )
            logger.debug(f"分块存在: {bucket}/{object_name}")
            return True
            
        except Exception as e:
            # 对象不存在的异常是正常的，不记录为错误
            if "NoSuchKey" in str(e) or "not found" in str(e).lower():
                logger.debug(f"分块不存在: {bucket}/{object_name}")
            else:
                logger.warning(f"检查分块存在性错误 {bucket}/{object_name}: {e}")
            return False
    
    async def delete_chunk(
        self,
        bucket: str,
        object_name: str
    ) -> bool:
        """删除指定的分块对象"""
        try:
            # 先检查对象是否存在
            exists = await self.chunk_exists(bucket, object_name)
            if not exists:
                logger.warning(f"分块不存在，无法删除: {bucket}/{object_name}")
                return True  # 对象不存在也算删除成功
            
            # 删除对象
            await self._run_in_thread(
                self.minio.remove_object,
                bucket,
                object_name
            )
            
            logger.info(f"成功删除分块: {bucket}/{object_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除分块失败 {bucket}/{object_name}: {e}")
            return False
    
    # ==================== 多部分上传操作 ====================
    
    async def complete_multipart_upload(
        self,
        bucket: str,
        object_name: str,
        parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """完成分块上传 - 正确的MinIO多部分上传实现"""
        try:
            logger.info(f"开始完成分块上传 {object_name}，共 {len(parts)} 个分块")
            
            # 确保存储桶存在
            await self._ensure_bucket_exists(bucket)
            
            if not parts:
                return {"success": False, "error": "未提供分块"}
            
            # 使用MinIO的多部分上传API
            try:
                # 创建多部分上传会话
                upload_id = await self._run_in_thread(
                    self.minio.create_multipart_upload,
                    bucket,
                    object_name,
                    "application/octet-stream"
                )
                logger.info(f"创建多部分上传会话: {upload_id}")
                
                # 上传所有分块
                uploaded_parts = []
                for part in parts:
                    part_number = part.get("part_number", 1)
                    # 从存储中获取分块数据
                    chunk_object_name = f"{object_name}.part{part_number}"
                    
                    try:
                        chunk_data = await self.download_chunk(bucket, chunk_object_name)
                        
                        # 上传分块到多部分上传会话
                        etag = await self._run_in_thread(
                            self.minio.upload_part,
                            bucket,
                            object_name,
                            upload_id,
                            part_number,
                            chunk_data
                        )
                        
                        uploaded_parts.append({
                            "PartNumber": part_number,
                            "ETag": etag
                        })
                        logger.info(f"上传分块 {part_number}, ETag: {etag}")
                        
                    except Exception as e:
                        logger.error(f"上传分块 {part_number} 失败: {e}")
                        # 中止上传会话
                        await self._run_in_thread(
                            self.minio.abort_multipart_upload,
                            bucket,
                            object_name,
                            upload_id
                        )
                        return {
                            "success": False,
                            "error": f"上传分块 {part_number} 失败: {str(e)}"
                        }
                
                # 完成多部分上传
                await self._run_in_thread(
                    self.minio.complete_multipart_upload,
                    bucket,
                    object_name,
                    upload_id,
                    uploaded_parts
                )
                logger.info(f"完成多部分上传: {object_name}")
                
                # 清理临时分块文件
                await self._cleanup_temp_parts(bucket, object_name, len(parts))
                
                return {
                    "success": True,
                    "etag": f"multipart-{generate_uuid()}",
                    "object_name": object_name,
                    "message": "多部分上传成功完成",
                    "total_parts": len(parts)
                }
                
            except Exception as e:
                logger.error(f"多部分上传失败: {e}")
                return {
                    "success": False,
                    "error": f"多部分上传失败: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"完成多部分上传失败 - 存储桶: {bucket}, 对象: {object_name}, 错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cleanup_temp_parts(self, bucket: str, object_name: str, total_parts: int):
        """清理临时分块文件"""
        try:
            deleted_count = 0
            for part_number in range(1, total_parts + 1):
                chunk_object_name = f"{object_name}.part{part_number}"
                success = await self.delete_chunk(bucket, chunk_object_name)
                if success:
                    deleted_count += 1
            
            logger.info(f"清理临时分块 {deleted_count}/{total_parts} 个: {object_name}")
            
        except Exception as e:
            logger.warning(f"清理部分临时分块失败: {e}")
    
    # ==================== 文件组合操作 ====================
    
    async def _multi_stage_compose(
        self,
        bucket: str,
        target_object: str,
        parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """多阶段组合文件（处理超过32个分块的情况）"""
        try:
            # 分组组合，每32个分块一组
            chunk_size = 32
            groups = [parts[i:i + chunk_size] for i in range(0, len(parts), chunk_size)]
            intermediate_objects = []
            
            # 第一阶段：组合每组分块
            for i, group in enumerate(groups):
                intermediate_object = f"{target_object}_temp_{i}"
                
                source_objects = []
                for part in group:
                    chunk_object_name = f"{target_object}/part_{part['part_number']}"
                    source_objects.append(
                        await self._run_in_thread(
                            self.minio.compose_source,
                            bucket,
                            chunk_object_name
                        )
                    )
                
                await self._run_in_thread(
                    self.minio.compose_object,
                    bucket,
                    intermediate_object,
                    source_objects
                )
                intermediate_objects.append(intermediate_object)
            
            # 第二阶段：组合所有中间对象
            if len(intermediate_objects) == 1:
                # 如果只有一个中间对象，直接重命名
                await self._run_in_thread(
                    self.minio.copy_object,
                    bucket,
                    target_object,
                    self.minio.CopySource(bucket, intermediate_objects[0])
                )
                # 删除中间对象
                await self._run_in_thread(
                    self.minio.remove_object,
                    bucket,
                    intermediate_objects[0]
                )
            else:
                # 组合所有中间对象
                source_objects = []
                for obj in intermediate_objects:
                    source_objects.append(
                        await self._run_in_thread(
                            self.minio.compose_source,
                            bucket,
                            obj
                        )
                    )
                
                result = await self._run_in_thread(
                    self.minio.compose_object,
                    bucket,
                    target_object,
                    source_objects
                )
                
                # 清理中间对象
                for obj in intermediate_objects:
                    await self._run_in_thread(
                        self.minio.remove_object,
                        bucket,
                        obj
                    )
            
            logger.info(f"多阶段组合完成，共 {len(parts)} 个分块: {target_object}")
            return {
                "success": True,
                "etag": "multi-stage-completed"
            }
            
        except Exception as e:
            logger.error(f"多阶段组合失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def compose_file_from_chunks(
        self,
        bucket_name: str,
        target_object_name: str,
        chunk_object_names: List[str],
        content_type: str = "application/octet-stream"
    ) -> str:
        """从分块组合完整文件"""
        try:
            await self._ensure_bucket_exists(bucket_name)
            
            source_objects = []
            for chunk_object_name in chunk_object_names:
                source_objects.append(
                    await self._run_in_thread(
                        self.minio.compose_source,
                        bucket_name,
                        chunk_object_name
                    )
                )
            
            # 处理超过32个分块的情况
            if len(source_objects) <= 32:
                etag = await self._run_in_thread(
                    self.minio.compose_object,
                    bucket_name,
                    target_object_name,
                    source_objects
                )
            else:
                # 使用多阶段组合
                parts = [{"part_number": i + 1} for i in range(len(chunk_object_names))]
                result = await self._multi_stage_compose(bucket_name, target_object_name, parts)
                if result["success"]:
                    etag = result.get("etag", "composed")
                else:
                    raise Exception(result["error"])
            
            # 设置对象元数据
            await self._run_in_thread(
                self.minio.copy_object,
                bucket_name,
                target_object_name,
                await self._run_in_thread(
                    self.minio.CopySource,
                    bucket_name,
                    target_object_name
                ),
                metadata_directive="REPLACE",
                content_type=content_type
            )
            
            logger.info(f"文件组合成功，共 {len(chunk_object_names)} 个分块: {target_object_name}")
            return etag
            
        except Exception as e:
            logger.error(f"MinIO文件组合失败 - 存储桶: {bucket_name}, 目标: {target_object_name}, 错误: {e}")
            raise ExternalServiceError("MinIO", "compose_file_from_chunks", str(e))
    
    # ==================== 元数据和列表操作 ====================
    
    async def get_chunk_metadata(
        self,
        bucket: str,
        object_name: str
    ) -> Dict[str, Any]:
        """获取分块元数据"""
        try:
            stat = await self._run_in_thread(
                self.minio.stat_object,
                bucket,
                object_name
            )
            
            return {
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
            
        except Exception as e:
            logger.error(f"获取分块元数据失败 - 存储桶: {bucket}, 对象: {object_name}, 错误: {e}")
            raise ExternalServiceError("MinIO", "get_chunk_metadata", str(e))
    
    async def list_chunks(
        self,
        bucket: str,
        prefix: str,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """列出指定前缀的所有分块"""
        try:
            objects = await self._run_in_thread(
                self.minio.list_objects,
                bucket,
                prefix=prefix,
                recursive=recursive
            )
            
            chunks = []
            for obj in objects:
                chunks.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "is_dir": obj.is_dir
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"列出分块失败 - 存储桶: {bucket}, 前缀: {prefix}, 错误: {e}")
            raise ExternalServiceError("MinIO", "list_chunks", str(e))
    
    async def cleanup_chunks(
        self,
        bucket: str,
        prefix: str
    ) -> int:
        """清理指定前缀的所有分块"""
        try:
            chunks = await self.list_chunks(bucket, prefix)
            
            deleted_count = 0
            for chunk in chunks:
                if not chunk["is_dir"]:
                    await self.delete_chunk(bucket, chunk["object_name"])
                    deleted_count += 1
            
            logger.info(f"清理分块 {deleted_count} 个，前缀: {prefix}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理分块失败 - 存储桶: {bucket}, 前缀: {prefix}, 错误: {e}")
            raise ExternalServiceError("MinIO", "cleanup_chunks", str(e))
    
    # ==================== 预签名URL操作 ====================
    
    async def generate_presigned_url(
        self,
        bucket: str,
        object_name: str,
        method: str = "GET",
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """生成预签名URL"""
        try:
            if method.upper() == "GET":
                url = await self._run_in_thread(
                    self.minio.presigned_get_object,
                    bucket,
                    object_name,
                    expires=expires
                )
            elif method.upper() == "PUT":
                url = await self._run_in_thread(
                    self.minio.presigned_put_object,
                    bucket,
                    object_name,
                    expires=expires
                )
            elif method.upper() == "DELETE":
                url = await self._run_in_thread(
                    self.minio.presigned_delete_object,
                    bucket,
                    object_name,
                    expires=expires
                )
            else:
                raise ValueError(f"不支持的方法: {method}")
            
            logger.debug(f"生成预签名URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"生成预签名URL失败 - 存储桶: {bucket}, 对象: {object_name}, 方法: {method}, 错误: {e}")
            raise ExternalServiceError("MinIO", "generate_presigned_url", str(e))
    
    # ==================== 校验和计算 ====================
    
    async def calculate_checksums(self, chunk_data: bytes) -> Dict[str, str]:
        """计算分块数据的校验和"""
        try:
            return {
                "md5": hashlib.md5(chunk_data).hexdigest(),
                "sha256": hashlib.sha256(chunk_data).hexdigest(),
                "sha1": hashlib.sha1(chunk_data).hexdigest()
            }
        except Exception as e:
            logger.error(f"计算校验和失败: {e}")
            raise ExternalServiceError("MinIO", "calculate_checksums", str(e))


# 全局MinIO仓库实例
minio_repository = MinIORepository()