# foxmask/core/beanie.py
from typing import List, Type
import logging
from beanie import init_beanie
from foxmask.core.mongo import mongo_connection

logger = logging.getLogger(__name__)

class BeanieManager:
    """Beanie ODM 管理类"""
    
    async def initialize(self, document_models: List[Type]):
        """初始化 Beanie 文档模型"""
        try:
            if not mongo_connection.is_connected:
                await mongo_connection.connect()
            
            await init_beanie(
                database=mongo_connection.database,
                document_models=document_models
            )
            
            logger.info(f"Beanie initialized with {len(document_models)} document models")
            
        except Exception as e:
            logger.error(f"Failed to initialize Beanie: {e}", exc_info=True)
            raise

    async def initialize_from_modules(self):
        """从模块自动发现并初始化模型"""
        try:
            document_models = []
            
            # 文件域模型
            try:
                from foxmask.file.models import File, FileChunk, FileAccessLog, FileVersion
                document_models.extend([File, FileChunk, FileAccessLog, FileVersion])
                logger.debug("File domain models registered")
            except ImportError as e:
                logger.warning(f"File models not available: {e}")
            
            # 认证域模型
            try:
                from foxmask.auth.models import User, Session, Permission
                document_models.extend([User, Session, Permission])
                logger.debug("Auth domain models registered")
            except ImportError as e:
                logger.warning(f"Auth models not available: {e}")
            
            # 标签域模型
            try:
                from foxmask.tag.models import Tag, TagGroup
                document_models.extend([Tag, TagGroup])
                logger.debug("Tag domain models registered")
            except ImportError as e:
                logger.warning(f"Tag models not available: {e}")
            
            if document_models:
                await self.initialize(document_models)
            else:
                logger.warning("No document models found for Beanie initialization")
                
        except Exception as e:
            logger.error(f"Failed to initialize Beanie from modules: {e}")

# 全局 Beanie 管理器实例
beanie_manager = BeanieManager()