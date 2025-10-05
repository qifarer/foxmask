# -*- coding: utf-8 -*-
import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4

from foxmask.knowledge_item.domain import (
    KnowledgeItemStatusEnum,
    KnowledgeItemTypeEnum,
    ItemContentTypeEnum,
    KnowledgeItemEntity,
    KnowledgeItemContentEntity,
)
from foxmask.knowledge_item.repositories import (
    knowledge_item_repository,
)
from foxmask.file.models import FileType,FileStatus
from foxmask.utils.pdf_parser import pdf_parser, PDFMetadata
from foxmask.utils.chunk_content import chunk_markdown_content
from foxmask.utils.minio_client import minio_client

from foxmask.core.logger import logger
from foxmask.file.repositories import file_repository

from foxmask.knowledge_item.dto import (
    KnowledgeItemCreateDTO, KnowledgeItemContentCreateDTO,
    KnowledgeItemWithContentsCreateDTO,
    KnowledgeItemUpdateDTO, FileProcessingRequestDTO
)
from foxmask.knowledge_item.services import knowledge_item_service

class KnowledgeParserService:
    """知识条目解析服务"""
    
    def __init__(self):
        self.pdf_parser = pdf_parser
        self.item_repo = knowledge_item_repository
        
    async def parse_file_to_item_md(
        self,
        tenant_id: str,
        file_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
               # 获取文件对象
            file = await file_repository.get_file_by_file_id(file_id)
            if not file:
                logger.error(f"文件不存在: {file_id}")
                return {
                    "status": "error",
                    "error": "文件不存在",
                    "message": f"File with ID {file_id} "
                }
            
            if file.file_type != FileType.PDF:
                logger.error(f"文件类型不支持: {file_id}-{file.file_type}")
                return {
                    "status": "error",
                    "error": "文件类型不支持",
                    "message": f"文件类型不支持 {file_id}-{file.file_type} "
                }     
            
            if file.status != FileStatus.UPLOADED:
                logger.error(f"文件状态异常: {file_id}-{file.status}")
                return {
                    "status": "error",
                    "error": "文件状态异常",
                    "message": f"文件状态异常 {file_id}-{file.status} "
                }     
            
            item = self.item_repo.get_item_by_source_id(file_id)
            if item:
                logger.error(f"知识条码已创建: {file_id}")
                return {
                    "status": "error",
                    "error": "知识条码已创建",
                    "message": f"知识条码已创建 {file_id} "
                }
           
           
            bucket_name = file.minio_bucket    
            object_name = file.minio_object_name
            
            if not bucket_name or not object_name:
                logger.error(f"文件存储地址错误：{file_id}")
                raise ValueError(f"文件存储地址错误：{file_id}")
            
            
            # 创建临时文件路径
            temp_dir = f"/tmp/{tenant_id}"
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = f"{temp_dir}/{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            try:
                # 从MinIO下载文件
                download_success = await minio_client.download_file(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=temp_file_path
                )
                
                if not download_success:
                    raise Exception("Failed to download file from MinIO")
                
                logger.info(f"Successfully downloaded file from MinIO: {bucket_name}/{object_name}")
                
                # 解析PDF文件
                md_content, md_metadata = pdf_parser.parse_pdf_to_markdown(temp_file_path)
                if not md_content:
                    raise Exception("Both Markdown extraction failed")
                if hasattr(md_metadata, 'model_dump'):
                    metadata_dict = md_metadata.model_dump()
                elif hasattr(md_metadata, '__dict__'):
                    metadata_dict = md_metadata.__dict__
                else:
                    metadata_dict = md_metadata or {}
                # md_content 进行分块, 保存在item content 中
                chunks = chunk_markdown_content(md_content,metadata_dict)

                 # 使用DTO创建知识条目
                item_create_dto = KnowledgeItemCreateDTO(
                    tenant_id=file.tenant_id,
                    item_type=KnowledgeItemTypeEnum.FILE,
                    source_id=file_id,
                    title=file.filename,
                    description=file.description,
                    metadata={
                        "type": file.filename,
                        "name": file.minio_object_name,
                        "path": file.minio_bucket,
                        "url": file.url,
                        "keyword": file_id,
                        "size": file.file_size,
                        "updateAt": file.created_at,      
                    },
                    tags=["FILE"],
                    note=str(metadata_dict),                   
                    visibility=file.visibility,
                    created_by="SYSTEM",
                    allowed_users=file.allowed_users,
                    allowed_roles=file.allowed_roles
                )
 
                # 创建知识内容
                contents_create_dto: List[KnowledgeItemContentCreateDTO]=[]
                for chunk in chunks:
                    content_create_dto = KnowledgeItemContentCreateDTO(
                        src_id=str(uuid4()),
                        src_title=file.filename, # chunk.metadata.get('file_name',""),
                        src_summary=chunk.metadata.get('source',""),
                        src_keyword=chunk.metadata.get('Header 1',""),
                        cnt_type=ItemContentTypeEnum.MD,
                        cnt_text=chunk.page_content,
                        cnt_summary=file.filename,
                        cnt_tags=[],
                        metadata={},
                        created_by="SYSTEM"
                    )
                    contents_create_dto.append(content_create_dto)

                item_contents_create_dto = KnowledgeItemWithContentsCreateDTO(
                    item=item_create_dto,contents=contents_create_dto
                )
                # 创建知识条目
                item_conents_dto = await knowledge_item_service.create_knowledge_item_with_contents(item_contents_create_dto)
                
                #
                update_dto = KnowledgeItemUpdateDTO(
                    status = KnowledgeItemStatusEnum.CREATED
                )
                update_dto = await knowledge_item_service.update_knowledge_item(item_id=item_conents_dto.item.item_id,update_dto=update_dto)
                if  not update_dto:
                    raise Exception(f"创建知识条目和内容未完成:{item_conents_dto.item.item_id}")
                
                await file_repository.update_file_status(file_id=file_id,status=FileStatus.COMPLETED)
                return item_conents_dto
                
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up temporary file: {cleanup_error}")
                    
        except ValueError as e:
            logger.error(f"Error parse knowledge ValueError MD from PDF: {e}")
                
            return None
            
    async def parse_knowledge_item_to_md(
        self,
        item_id: str,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            # 获取知识条目
            item = self.item_repo.get_item_by_id(item_id=item_id)
            if not item:
                raise ValueError(f"knowledge item not found: item_id={item_id},tenant_id={tenant_id}")
            
            # 验证条目类型和状态
            if not (item.item_type == KnowledgeItemTypeEnum.FILE and item.status == KnowledgeItemStatusEnum.CREATED):
                raise ValueError(f"error for knowledge item: item_type={item.item_type},status={item.status}")
            
            # 获取源文件信息
            source = item.content.get('source', {})
            if not source:
                logger.error(f"knowledge item source not found: item_id={item_id},tenant_id={tenant_id}")
                raise ValueError(f"knowledge item source not found: item_id={item_id},tenant_id={tenant_id}")
            
            bucket_name = source.get("data", {}).get("bucket_name", "")
            object_name = source.get("data", {}).get("object_name", "")  # 修正为object_name
            
            if not bucket_name or not object_name:
                logger.error(f"Missing bucket_name or object_name in source data: {source}")
                raise ValueError("Missing bucket_name or object_name in source data")
            
            # 更新状态为处理中
            self.item_repo.update_item_status(
                item_id=item_id,
                tenant_id=tenant_id,
                status=KnowledgeItemStatusEnum.PARSING,
                processing_metadata={
                    "started_at": datetime.now().isoformat(),
                    "action": "pdf_parsing"
                }
            )
            
            # 创建临时文件路径
            temp_dir = f"/tmp/{tenant_id}"
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = f"{temp_dir}/{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            try:
                # 从MinIO下载文件
                download_success = await minio_client.download_file(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=temp_file_path
                )
                
                if not download_success:
                    raise Exception("Failed to download file from MinIO")
                
                logger.info(f"Successfully downloaded file from MinIO: {bucket_name}/{object_name}")
                
                # 解析PDF文件
                md_content, metadata, stats = pdf_parser.parse_pdf_to_markdown(temp_file_path)
                
                if not md_content:
                    raise Exception("Both Markdown extraction failed")
                # md_content 进行分块, 保存在item content 中
                chunks = chunk_markdown_content(md_content,metadata)

               

                # 保存Markdown内容
                content_data = {
                    "content_type": "markdown",
                    "content": md_content,
                    "processing_stats": stats,
                    "metadata": {
                        "original_filename": object_name,
                        "title": metadata.title if metadata else None,
                        "author": metadata.author if metadata else None,
                        "creation_date": metadata.creation_date if metadata else None,
                        "parsed_at": datetime.now().isoformat(),
                        "parser_version": "1.0"
                    }
                }
                
                # 更新知识条目内容
                update_data = {
                    "content": content_data,
                    "status": KnowledgeItemStatusEnum.COMPLETED,
                    "processing_metadata": {
                        **stats,
                        "completed_at": datetime.now().isoformat(),
                        "content_type": "markdown"
                    }
                }
                
                # 如果解析出标题，更新条目标题
                if metadata and metadata.title and metadata.title.strip():
                    update_data["title"] = metadata.title
                
                self.item_repo.update_item(
                    item_id=item_id,
                    tenant_id=tenant_id,
                    update_data=update_data
                )

                
                logger.info(f"Successfully parsed PDF to markdown: {len(md_content)} characters")
                
                return {
                    "success": True,
                    "content_type": "markdown",
                    "content_length": len(md_content),
                    "stats": stats,
                    "item_id": item_id,
                    "metadata": {
                        "title": metadata.title if metadata else None,
                        "author": metadata.author if metadata else None,
                        "pages": stats.get("total_pages", 0)
                    }
                }
                
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up temporary file: {cleanup_error}")
                    
        except ValueError as e:
            logger.error(f"Error parse knowledge ValueError MD from PDF: {e}")
            
            # 更新状态为失败
            try:
                self.item_repo.update_item_status(
                    item_id=item_id,
                    tenant_id=tenant_id,
                    status=KnowledgeItemStatusEnum.FAILED,
                    error_info={
                        "error": str(e),
                        "failed_at": datetime.now().isoformat(),
                        "error_type": "validation_error"
                    }
                )
            except Exception:
                pass
                
            return None
            
        except Exception as e:
            logger.error(f"Error parse knowledge MD from PDF: {e}")
            
            # 更新状态为失败
            try:
                self.item_repo.update_item_status(
                    item_id=item_id,
                    tenant_id=tenant_id,
                    status=KnowledgeItemStatusEnum.FAILED,
                    error_info={
                        "error": str(e),
                        "failed_at": datetime.now().isoformat(),
                        "error_type": "processing_error"
                    }
                )
            except Exception:
                pass
                
            return None
  
    async def parse_knowledge_item_to_json(
        self,
        item_id: str,
        tenant_id: str,
    ) -> Optional[Dict[str,Any]]:
        try:
            item =  self.item_repo.get_item_by_id(item_id=item_id)
            if not item:
                raise ValueError(f"knowledge item not found: item_id={item_id},tenant_id={tenant_id}")
            if not (item.item_type == KnowledgeItemTypeEnum.FILE and item.status == KnowledgeItemStatusEnum.CREATED):
                raise ValueError(f"error for knowledge item: item_type={item.item_type},status={item.status }")
            source = item.content.get('source',{})
            if not source:
                logger.error(f"knowledge item source not found: item_id={item_id},tenant_id={tenant_id}")
                raise ValueError(f"knowledge item source not found: item_id={item_id},tenant_id={tenant_id}")
            bucket_name = source.get("data",{}).get("bucket_name","")
            object_name = source.get("data",{}).get("bucket_name","")
            
            url = await minio_client.get_presigned_url(bucket_name=bucket_name,object_name=object_name)
            
        except ValueError as e:  
            logger.error(f"Error parse knowledge ValueError MD from PDF: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parse knowledge MD from PDF: {e}")
            return None
        
    
    async def parse_knowledge_item_to_pdf(
        self,
        item_id: str,
        file_name: str,
        tenant_id: str,
        created_by: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        visibility: str = "private"
    ) -> Optional[KnowledgeItemEntity]:
        """从PDF文件创建知识条目"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_name):
                logger.error(f"PDF file not found: {file_name}")
                return None
            
            file_size = os.path.getsize(file_name)
            
            # 创建知识条目数据
            item_data = {
                "title": os.path.splitext(file_name)[0],  # 默认使用文件名作为标题
                "description": description,
                "item_type": KnowledgeItemTypeEnum.FILE,
                "source": PDFSource(
                    file_path=file_name,
                    file_name=file_name,
                    file_size=file_size,
                    upload_date=datetime.now()
                ),
                "status": KnowledgeItemStatusEnum.PENDING,
                "tags": tags or [],
                "category": category,
                "visibility": visibility,
                "tenant_id": tenant_id,
                "created_by": created_by
            }
            
            # 创建知识条目
            item = self.item_repo.create_item(item_data)
            logger.info(f"Created knowledge item: {item.id}")
            
            return item
            
        except Exception as e:
            logger.error(f"Error creating knowledge item from PDF: {e}")
            return None
    
    async def process_knowledge_item(
        self,
        item_id: str,
        tenant_id: str
    ) -> bool:
        """处理知识条目，解析PDF内容"""
        try:
            # 获取知识条目
            item = self.item_repo.get_item_by_id(item_id)
            if not item:
                logger.error(f"Knowledge item {item_id} not found")
                return False
            
            # 检查是否为PDF文档类型
            if item.item_type != KnowledgeItemTypeEnum.FILE:
                logger.error(f"Item {item_id} is not a document type")
                return False
            
            # 检查源文件是否存在
            if not item.source or not os.path.exists(item.source.file_path):
                logger.error(f"Source file not found for item {item_id}")
                self.item_repo.update_item_status(
                    item_id, tenant_id, KnowledgeItemStatusEnum.FAILED,
                    error_info={"error": "Source file not found"}
                )
                return False
            
            # 更新状态为处理中
            self.item_repo.update_item_status(
                item_id, tenant_id, KnowledgeItemStatusEnum.PENDING,
                processing_metadata={"started_at": datetime.now().isoformat()}
            )
            
            logger.info(f"Processing knowledge item {item_id}: {item.source.file_name}")
            
            # 解析PDF文件
            md_content, metadata, stats = self.pdf_parser.parse_pdf_to_markdown(
                item.source.file_path
            )
            
            if md_content is None:
                # 如果Markdown解析失败，尝试提取纯文本
                logger.warning(f"Markdown parsing failed for item {item_id}, falling back to text extraction")
                text_content, text_stats = self.pdf_parser.parse_pdf_to_text(item.source.file_path)
                
                if text_content:
                    # 保存文本内容
                    await self._save_content(
                        item_id, tenant_id, text_content,
                        ItemContentTypeEnum.PARSED, text_stats
                    )
                    
                    # 更新条目状态和统计信息
                    self.item_repo.update_item_status(
                        item_id, tenant_id, KnowledgeItemStatusEnum.COMPLETED,
                        processing_metadata=text_stats
                    )
                    
                    logger.info(f"Text extraction completed for item {item_id}")
                    return True
                else:
                    # 完全失败
                    self.item_repo.update_item_status(
                        item_id, tenant_id, KnowledgeItemStatusEnum.FAILED,
                        error_info={"error": "Both Markdown and text extraction failed"}
                    )
                    logger.error(f"Both Markdown and text extraction failed for item {item_id}")
                    return False
            
            # 保存Markdown内容
            await self._save_content(
                item_id, tenant_id, md_content,
                ItemContentTypeEnum.PARSED, stats
            )
            
            # 更新条目元数据
            update_data = {}
            if metadata and metadata.title and not item.title.startswith(item.source.file_name):
                update_data["title"] = metadata.title
            
            if metadata:
                update_data["metadata"] = {
                    "author": metadata.author,
                    "subject": metadata.subject,
                    "keywords": metadata.keywords,
                    "creation_date": metadata.creation_date,
                    "modification_date": metadata.mod_date
                }
            
            if update_data:
                self.item_repo.update_item(item_id, tenant_id, update_data)
            
            # 更新状态为完成
            self.item_repo.update_item_status(
                item_id, tenant_id, KnowledgeItemStatusEnum.COMPLETED,
                processing_metadata=stats
            )
            
            logger.info(f"Successfully processed knowledge item {item_id}")
            logger.info(f"Stats: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing knowledge item {item_id}: {e}")
            
            # 更新状态为失败
            self.item_repo.update_item_status(
                item_id, tenant_id, KnowledgeItemStatusEnum.FAILED,
                error_info={"error": str(e), "traceback": str(e.__traceback__)}
            )
            
            return False
    
    async def _save_content(
        self,
        item_id: str,
        tenant_id: str,
        content: str,
        content_type: ItemContentTypeEnum,
        stats: Dict[str, Any]
    ) -> Optional[KnowledgeItemContentEntity]:
        """保存解析后的内容"""
        try:
            content_data = {
                "item_id": item_id,
                "content_type": content_type,
                "content": content,
                "processing_stats": stats,
                "is_latest": True,
                "version": 1,  # 会自动递增
                "tenant_id": tenant_id,
                "created_by": "system"  # 系统自动创建
            }
            
            content_obj = await self.content_repo.create_new_content_version(
                content_data, tenant_id
            )
            
            logger.info(f"Saved {content_type} content for item {item_id}, version {content_obj.version}")
            return content_obj
            
        except Exception as e:
            logger.error(f"Error saving content for item {item_id}: {e}")
            return None
    
    async def batch_process_items(
        self,
        item_ids: List[str],
        tenant_id: str,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """批量处理知识条目"""
        results = {
            "total": len(item_ids),
            "success": 0,
            "failed": 0,
            "completed": 0,
            "details": []
        }
        
        # 简单的顺序处理（可以改为并发处理）
        for item_id in item_ids:
            try:
                success = await self.process_knowledge_item(item_id, tenant_id)
                
                result_detail = {
                    "item_id": item_id,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }
                
                if success:
                    results["success"] += 1
                    result_detail["status"] = "success"
                else:
                    results["failed"] += 1
                    result_detail["status"] = "failed"
                
                results["details"].append(result_detail)
                
            except Exception as e:
                logger.error(f"Error in batch processing item {item_id}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "item_id": item_id,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        results["completed"] = results["success"] + results["failed"]
        return results
    
    async def reprocess_failed_items(
        self,
        tenant_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """重新处理失败的知识条目"""
        # 获取所有失败状态的条目
        failed_items = self.item_repo.list_items(
            tenant_id=tenant_id,
            status=KnowledgeItemStatusEnum.FAILED
        )
        
        item_ids = [str(item.id) for item in failed_items]
        
        logger.info(f"Found {len(item_ids)} failed items to reprocess")
        
        return await self.batch_process_items(item_ids, tenant_id)
    
    async def get_processing_stats(
        self,
        tenant_id: str
    ) -> Dict[str, Any]:
        """获取处理统计信息"""
        stats = {
            "total":  self.item_repo.count_items(tenant_id),
            "pending":  self.item_repo.count_items(
                tenant_id, status=KnowledgeItemStatusEnum.PENDING
            ),
            "processing":  self.item_repo.count_items(
                tenant_id, status=KnowledgeItemStatusEnum.PARSING
            ),
            "completed":  self.item_repo.count_items(
                tenant_id, status=KnowledgeItemStatusEnum.COMPLETED
            ),
            "failed":  self.item_repo.count_items(
                tenant_id, status=KnowledgeItemStatusEnum.FAILED
            )
        }
        
        stats["success_rate"] = (
            stats["completed"] / stats["total"] * 100
        ) if stats["total"] > 0 else 0
        
        return stats
    
    async def cleanup_old_content_versions(
        self,
        tenant_id: str,
        keep_versions: int = 3
    ) -> Dict[str, Any]:
        """清理旧的内容版本"""
        # 实现版本清理逻辑
        # 这里需要根据实际需求实现具体的清理策略
        return {"cleaned": 0, "remaining": 0}


# 全局服务实例
knowledge_parser_service = KnowledgeParserService()