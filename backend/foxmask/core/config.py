# Configuration file for the Foxmask application
from pydantic_settings import BaseSettings
from pydantic import Field, RedisDsn, MongoDsn, AnyUrl, SecretStr
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = Field("Foxmask", env="APP_NAME")
    APP_VERSION: str = Field("0.1.0", env="APP_VERSION")
    DEBUG: bool = Field(True, env="DEBUG")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    
    # Server
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8888, env="PORT")
    
    # MongoDB
    MONGODB_URI: MongoDsn = Field("mongodb://localhost:27017", env="MONGODB_URI")
    MONGODB_DB_NAME: str = Field("foxmask", env="MONGODB_DB_NAME")
    MONGODB_MAX_POOL_SIZE: int = Field(100, env="MONGODB_MAX_POOL_SIZE")
    MONGODB_MIN_POOL_SIZE: int = Field(10, env="MONGODB_MIN_POOL_SIZE")
    
    DEFAULT_TENANT_ID: str =  Field("foxmask", env="DEFAULT_TENANT_ID") 
    DEFAULT_TENANT_NAME: str =  Field("Foxmask", env="DEFAULT_TENANT_NAME")
    
    # MinIO 配置
    MINIO_USE_TENANT_BUCKETS: bool = Field(True, env="MINIO_USE_TENANT_BUCKETS")
    # = True  # 是否为每个租户创建独立存储桶
    MINIO_DEFAULT_BUCKET: str = Field("foxmask", env="MINIO_DEFAULT_BUCKET") 
    MINIO_BUCKET_PREFIX: str = Field("tt", env="MINIO_BUCKET_PREFIX") 
    
    # 文件存储路径配置
    FILE_STORAGE_PATH_FORMAT: str = "{tenant_id}/{year}{month}{day}/{filename}"
    
    # MinIO
    MINIO_ENDPOINT: str = Field("localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: SecretStr = Field(..., env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: SecretStr = Field(..., env="MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME: str = Field("foxmask", env="MINIO_BUCKET_NAME")
    MINIO_SECURE: bool = Field(False, env="MINIO_SECURE")
    MINIO_REGION: str = Field("us-east-1", env="MINIO_REGION")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field("localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_GROUP_ID: str = Field("foxmask-group", env="KAFKA_GROUP_ID")
    KAFKA_KNOWLEDGE_TOPIC: str = Field("KAFKA_KNOWLEDGE_TOPIC", env="KAFKA_KNOWLEDGE_TOPIC")
    
    # Weaviate
    WEAVIATE_URL: AnyUrl = Field("http://localhost:8080", env="WEAVIATE_URL")
    WEAVIATE_API_KEY: Optional[SecretStr] = Field(None, env="WEAVIATE_API_KEY")
    
    # Neo4j
    NEO4J_URI: AnyUrl = Field("bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field("neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: SecretStr = Field(..., env="NEO4J_PASSWORD")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(50, env="NEO4J_MAX_CONNECTION_POOL_SIZE")
    
    # Redis (optional for caching/sessions)
    REDIS_URI: Optional[RedisDsn] = Field(None, env="REDIS_URI")
    
    # Casdoor
    CASDOOR_ENDPOINT: str = Field(..., env="CASDOOR_ENDPOINT")
    CASDOOR_CLIENT_ID: str = Field(..., env="CASDOOR_CLIENT_ID")
    CASDOOR_CLIENT_SECRET: str = Field(..., env="CASDOOR_CLIENT_SECRET")
    CASDOOR_CERT: str = Field(..., env="CASDOOR_CERT")
    CASDOOR_ORG_NAME: str = Field(..., env="CASDOOR_ORG_NAME")
    CASDOOR_APP_NAME: str = Field(..., env="CASDOOR_APP_NAME")

    # API Key 配置
    API_KEY_HEADER: str = Field(default="X-API-Key")
    API_KEY_APP_NAME: str = Field(default="foxmask-api")
    API_KEY_DEFAULT_EXPIRE_DAYS: int = Field(default=365)
    
    # 权限配置
    API_KEY_PERMISSIONS: List[str] = Field(default=["read", "write", "delete", "admin"])
    
    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = Field(default=100)
    RATE_LIMIT_PER_HOUR: int = Field(default=5000)
    
    # 安全配置
    ALLOWED_ORIGINS: List[str] = Field(default=["*"])
 
    # Security
    SECRET_KEY: SecretStr = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    CORS_ORIGINS: list[str] = Field(["http://localhost:3000", "http://127.0.0.1:3000"], env="CORS_ORIGINS")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(100, env="RATE_LIMIT_PER_MINUTE")
    
    # File upload limits
    MAX_FILE_SIZE_MB: int = Field(100, env="MAX_FILE_SIZE_MB")
    ALLOWED_FILE_TYPES: list[str] = Field([
        "text/plain", "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/markdown", "text/csv", "application/json"
    ], env="ALLOWED_FILE_TYPES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略未定义的環境變數

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

settings = Settings()
