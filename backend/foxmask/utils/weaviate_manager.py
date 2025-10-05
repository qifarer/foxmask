# weaviate_manager.py
import weaviate
from weaviate.classes.config import Configure, Property, DataType, ReferenceProperty
from weaviate.classes.init import Auth,AdditionalConfig,Timeout
from typing import Optional, Dict, List, Any, Union
from enum import Enum
import os
from contextlib import contextmanager
import time

from foxmask.core.config import settings
from foxmask.core.logger import logger

class WeaviateClass(str, Enum):
    """Weaviate class names"""
    KNOWLEDGE_ITEM = "KnowledgeItem"
    KNOWLEDGE_ITEM_CONTENT = "KnowledgeItemContent"

class WeaviateDistanceMetric(str, Enum):
    """Weaviate distance metrics"""
    COSINE = "cosine"
    EUCLIDEAN = "l2-squared"
    DOT = "dot"

class WeaviateClientManager:
    """Weaviate client manager with connection pooling and retry logic"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WeaviateClientManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Weaviate client"""
        self._client = None
        self.connected = False
        self.max_retries = 3
        self.retry_delay = 1
    
    def get_client(self) -> weaviate.Client:
        """Get Weaviate client with connection management"""
        if self._client is None or not self.connected:
            self._connect_with_retry()
        return self._client
    
    def _connect_with_retry(self):
        """Connect to Weaviate with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self._connect()
                self.connected = True
                logger.info("Successfully connected to Weaviate")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("All connection attempts failed")
                    raise
    
    def _connect(self):
        """Connect to Weaviate (local deployment)"""
        try:
            # Local Weaviate deployment with multiple connection options
            
            # Add authentication if configured
            #api_key = os.getenv('WEAVIATE_API_KEY')
            #if api_key:
             #   connection_params['auth_credentials'] = Auth.api_key(api_key)
            
            self._client = weaviate.connect_to_local(
                host=settings.WEAVIATE_HOST,
                port=settings.WEAVIATE_PORT,
                grpc_port=settings.WEAVIATE_GRPC_PORT,
                additional_config=AdditionalConfig(
                    timeout=Timeout(init=settings.WEAVIATE_INITIALIZE_TIMEOUT, 
                                    query=settings.WEAVIATE_QUERY_TIMEOUT, 
                                    insert=settings.WEAVIATE_INSERT_TIMEOUT)
                )
            )
            
            # Test connection
            self._client.collections.list_all()
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            self.connected = False
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for Weaviate connection"""
        client = self.get_client()
        try:
            yield client
        except Exception as e:
            logger.error(f"Weaviate connection error: {e}")
            self.connected = False
            raise
        finally:
            # Client is kept open for reuse in connection pool
            pass
    
    def close(self):
        """Close Weaviate connection"""
        if self._client:
            self._client.close()
            self.connected = False
            logger.info("Weaviate connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Weaviate health status"""
        try:
            with self.get_connection() as client:
                # Get server info
                server_info = client.get_meta()
                
                # Check collections
                collections = client.collections.list_all()
                
                return {
                    "status": "healthy",
                    "version": server_info.get("version", "unknown"),
                    "collections_count": len(collections),
                    "collections": collections,
                    "connected": self.connected
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": self.connected
            }
    
    def execute_with_retry(self, operation, *args, **kwargs):
        """Execute operation with retry logic"""
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Operation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    # Refresh connection if needed
                    if not self.connected:
                        self._connect_with_retry()
                else:
                    logger.error("All operation attempts failed")
                    raise

# Global client manager instance
weaviate_client_manager = WeaviateClientManager()