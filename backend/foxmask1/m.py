from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import time

from foxmask.core.mongo import connect_to_mongo, close_mongo_connection
from foxmask.core.minio import init_minio, close_minio
from foxmask.core.redis import init_redis, close_redis
from foxmask.core.kafka import init_kafka, close_kafka
from foxmask.core.config import settings

# 导入路由
from foxmask.file.routers import router as file_router
from foxmask.knowledge.routers import router as knowledge_router
from foxmask.knowledge.graphql import graphql_app as knowledge_graphql_app
from foxmask.tag.routers import router as tag_router
from foxmask.tag.graphql import graphql_app as tag_graphql_app
from foxmask.health.routers import router as health_router

# 导入中间件
from foxmask.middleware.file import FileSizeMiddleware
from foxmask.middleware.logging import LoggingMiddleware
from foxmask.middleware.auth import AuthMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    startup_time = time.time()
    logger.info("Starting application initialization...")
    
    try:
        # 初始化数据库连接
        logger.info("Connecting to MongoDB...")
        await connect_to_mongo()
        
        # 初始化Redis
        logger.info("Initializing Redis...")
        await init_redis()
        
        # 初始化MinIO
        logger.info("Initializing MinIO...")
        await init_minio()
        
        # 初始化Kafka
        logger.info("Initializing Kafka...")
        await init_kafka()
        
        startup_duration = time.time() - startup_time
        logger.info(f"Application initialized successfully in {startup_duration:.2f} seconds")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    finally:
        # 关闭连接
        shutdown_time = time.time()
        logger.info("Shutting down application...")
        
        try:
            await close_mongo_connection()
            await close_minio()
            await close_redis()
            await close_kafka()
            
            shutdown_duration = time.time() - shutdown_time
            logger.info(f"Application shut down successfully in {shutdown_duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# 创建FastAPI应用
app = FastAPI(
    title="Foxmask Knowledge Management System",
    description="A comprehensive knowledge management system with file storage and AI capabilities",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(LoggingMiddleware)  # 日志中间件
app.add_middleware(AuthMiddleware)     # 认证中间件
app.add_middleware(FileSizeMiddleware, max_file_size=settings.MAX_FILE_SIZE)  # 文件大小限制

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# GZip 压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(file_router, prefix="/api/v1", tags=["Files"])
app.include_router(knowledge_router, prefix="/api/v1", tags=["Knowledge"])
app.include_router(tag_router, prefix="/api/v1", tags=["Tags"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# 注册GraphQL路由
app.include_router(knowledge_graphql_app, prefix="/graphql/knowledge", tags=["GraphQL - Knowledge"])
app.include_router(tag_graphql_app, prefix="/graphql/tags", tags=["GraphQL - Tags"])

@app.get("/", include_in_schema=False)
async def root():
    """根路由"""
    return {
        "message": "Foxmask Knowledge Management System API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "graphql_knowledge": "/graphql/knowledge",
            "graphql_tags": "/graphql/tags",
            "api_v1": "/api/v1"
        }
    }

@app.get("/health", include_in_schema=False)
async def health_check():
    """健康检查"""
    from foxmask.core.mongo import mongo_client
    from foxmask.core.redis import redis_client
    from foxmask.core.minio import minio_client
    from foxmask.core.kafka import kafka_producer
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "mongodb": "connected" if mongo_client else "disconnected",
            "redis": "connected" if redis_client and await redis_client.ping() else "disconnected",
            "minio": "connected" if minio_client and minio_client.is_connected else "disconnected",
            "kafka": "connected" if kafka_producer and kafka_producer.is_connected else "disconnected"
        },
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }
    
    return health_status

@app.get("/info", include_in_schema=False)
async def info():
    """系统信息"""
    return {
        "app": "Foxmask Knowledge Management System",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "mongodb_database": settings.MONGODB_DB_NAME,
        "minio_endpoint": settings.MINIO_ENDPOINT,
        "kafka_brokers": settings.KAFKA_BROKERS,
        "redis_url": settings.REDIS_URL,
        "max_file_size": settings.MAX_FILE_SIZE,
        "cors_origins": settings.CORS_ORIGINS
    }

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        workers=settings.WORKERS
    )