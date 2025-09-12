from fastapi import FastAPI
from foxmask.core.exceptions import exception_handlers
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from foxmask.core.mongo import connect_to_mongo, close_mongo_connection
from foxmask.middleware.file import FileSizeMiddleware

from foxmask.file.routers import router as file_router
from foxmask.file.graphql import graphql_app as file_graphql_app
from foxmask.knowledge.routers import router as knowledge_router
from foxmask.knowledge.graphql import graphql_app as knowledge_graphql_app
from foxmask.tag.routers import router as tag_router
from foxmask.tag.graphql import graphql_app as tag_graphql_app
from foxmask.core.config import get_settings
settings = get_settings()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    try:
        await connect_to_mongo()
        logger.info("Database and Beanie initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield  # 应用程序运行期间
    
    # 关闭时清理资源
    await close_mongo_connection()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="File Upload Service", 
    version="1.0.0",
    lifespan=lifespan,
    exception_handlers=exception_handlers  # 注册异常处理器
)
app.add_middleware(FileSizeMiddleware)
# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(file_router, prefix="/api/v1", tags=["Files"])
app.include_router(knowledge_router, prefix="/api/v1", tags=["Knowledge"])
app.include_router(tag_router, prefix="/api/v1", tags=["Tags"])

# 注册GraphQL路由
app.include_router(file_graphql_app, prefix="/graphql/file", tags=["GraphQL - File"])
app.include_router(knowledge_graphql_app, prefix="/graphql/knowledge", tags=["GraphQL - Knowledge"])
app.include_router(tag_graphql_app, prefix="/graphql/tags", tags=["GraphQL - Tags"])

@app.get("/", include_in_schema=False)
async def root():
    """根路由"""
    return {
        "message": "Foxmask Knowledge Management System API",
        "version": settings.VERSION,
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

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8877)