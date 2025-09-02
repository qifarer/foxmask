from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from foxmask.core.mongo import connect_to_mongo, close_mongo_connection
from .middleware.file import FileSizeMiddleware
from .api.file import router as file_router
from .api.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    await connect_to_mongo()
    yield
    # 关闭时断开数据库连接
    await close_mongo_connection()

app = FastAPI(
    title="File Upload Service", 
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(upload_router)
app.include_router(file_router)

@app.get("/")
async def root():
    return {
        "message": "File Upload Service with MongoDB and MinIO",
        "timestamp": datetime.now().isoformat(),
        "status": "running"
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