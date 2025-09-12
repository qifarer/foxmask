# foxmask/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, RedisDsn, AnyUrl
from typing import List, Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    
    PROJECT_NAME: str = "Foxmask Document Management System"
    DEBUG: bool = Field(default=True, env="DEBUG")
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    GRAPHQL_STR: str = "/graphql"
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8888, env="PORT")
    
    SUPPORTED_FILE_TYPES: list = ["image/", "text/", "application/json"]
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIRECTORY: str = "uploads"
    CHUNK_SIZE: int = 8 * 1024 * 1024  # 8MB chunks for streaming

# MongoDB 配置
    MONGO_URI: Optional[str] = None  # 完整的连接字符串
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_DB: str = "foxmask"
    MONGO_USERNAME: Optional[str] = None
    MONGO_PASSWORD: Optional[str] = None
    MONGO_AUTH_SOURCE: str = "admin"
    MONGO_REPLICA_SET: Optional[str] = None
    MONGO_SSL: bool = False
    MONGO_MAX_POOL_SIZE: int = 100
    MONGO_MIN_POOL_SIZE: int = 10
    
    # 集合名称配置
    MONGO_FILE_COLLECTION: str = "files"
    MONGO_DOCS_COLLECTION: str = "documents"
    MONGO_KB_COLLECTION: str = "knowledge_bases"
    MONGO_USER_COLLECTION: str = "users"
    MONGO_AUDIT_COLLECTION: str = "audit_logs"
    
    # MongoDB
    MONGO_URI: str = Field(
        default="mongodb://localhost:27017", 
        env="MONGO_URI"
    )
    MONGO_DB: str = Field(default="foxmask", env="MONGO_DB")
    MONGO_FILE_COLLECTION: str = Field(
        default="files", 
        env="MONGO_FILE_COLLECTION"
    )
    MONGO_DOCS_COLLECTION: str = Field(
        default="documents", 
        env="MONGO_DOCS_COLLECTION"
    )
    MONGO_KB_COLLECTION: str = Field(
        default="knowledge_bases", 
        env="MONGO_KB_COLLECTION"
    )
    MONGO_USERNAME: Optional[str] = Field(default=None, env="MONGO_USERNAME")
    MONGO_PASSWORD: Optional[str] = Field(default=None, env="MONGO_PASSWORD")
    MONGO_AUTH_SOURCE: str = Field(default="admin", env="MONGO_AUTH_SOURCE")
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    MINIO_BUCKET: str = Field(default="documents", env="MINIO_BUCKET")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092", 
        env="KAFKA_BOOTSTRAP_SERVERS"
    )
    KAFKA_TOPIC_DOCUMENT_CREATED: str = "document-created"
    KAFKA_TOPIC_DOCUMENT_PARSED: str = "document-parsed"
    KAFKA_TOPIC_VECTORIZATION: str = "vectorization"
    
    # Redis
    REDIS_URI: RedisDsn = Field(
        default="redis://localhost:6379/0", 
        env="REDIS_URI"
    )
    
    # Casdoor
    CASDOOR_ENDPOINT: str = Field(
        default="https://casdoor.example.com", 
        env="CASDOOR_ENDPOINT"
    )
    CASDOOR_CLIENT_ID: str = Field(env="CASDOOR_CLIENT_ID")
    CASDOOR_CLIENT_SECRET: str = Field(env="CASDOOR_CLIENT_SECRET")
    # CASDOOR_CERT: str = Field(env="CASDOOR_CERT")
    
    CASDOOR_ISSUER: str = Field(env="CASDOOR_ISSUER")
    # CASDOOR_PUBLIC_KEY: str = Field(env="CASDOOR_PUBLIC_KEY")
    CASDOOR_TOKEN_COOKIE_NAME: str = Field(env="CASDOOR_TOKEN_COOKIE_NAME")
    CASDOOR_ORG: str = Field(env="CASDOOR_ORG")
    CASDOOR_APP: str = Field(env="CASDOOR_APP")
    CASDOOR_CERT: str = Field(env="CASDOOR_CERT")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="change-this-in-production", 
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 7,  # 7 days
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    
    # Weaviate
    WEAVIATE_URL: Optional[AnyUrl] = Field(
        default=None, 
        env="WEAVIATE_URL"
    )
    
    # Neo4j
    NEO4J_URI: Optional[AnyUrl] = Field(
        default=None, 
        env="NEO4J_URI"
    )
    NEO4J_USER: Optional[str] = Field(
        default=None, 
        env="NEO4J_USER"
    )
    NEO4J_PASSWORD: Optional[str] = Field(
        default=None, 
        env="NEO4J_PASSWORD"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()