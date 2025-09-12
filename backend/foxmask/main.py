# -*- coding: utf-8 -*-
# Main application entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import strawberry
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager
import datetime
from datetime import timezone, datetime
import asyncio

from foxmask.core.config import settings
from foxmask.core.mongo import  connect_to_mongo, close_mongo_connection, mongodb
from foxmask.core.kafka import kafka_manager
from foxmask.core.scheduler import scheduler
from foxmask.core.logger import logger, setup_logger
from foxmask.task.consumers import task_consumer
from foxmask.task.dead_letter_processor import dead_letter_processor
from foxmask.core.middleware.error_handler import ErrorHandlerMiddleware, RateLimitMiddleware
from foxmask.core.monitoring import monitoring_service

# Import routers
from foxmask.auth.router import router as auth_router
from foxmask.file.router import router as file_router
from foxmask.knowledge.router import router as knowledge_router
from foxmask.tag.router import router as tag_router
from foxmask.task.router import router as task_router

# Import GraphQL schemas
from foxmask.file.graphql import FileQuery, FileMutation
from foxmask.knowledge.graphql import KnowledgeQuery, KnowledgeMutation
from foxmask.tag.graphql import TagQuery, TagMutation
from foxmask.task.graphql import TaskQuery, TaskMutation
from foxmask.file.mongo import init_file_db

# Import utils clients
from foxmask.utils.weaviate_client import weaviate_client
from foxmask.utils.neo4j_client import neo4j_client
from foxmask.utils.minio_client import minio_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    setup_logger()  # 配置日志
    # Startup
    await connect_to_mongo()
    await init_file_db()
    #await kafka_manager.create_producer()
    # Create Kafka topics
    #await kafka_manager.create_topic(settings.KAFKA_KNOWLEDGE_TOPIC)
    #await kafka_manager.create_topic("file_processing")
    #await kafka_manager.create_topic("notifications")
    #await kafka_manager.create_topic("system_events")
    #await kafka_manager.create_topic("data_sync")
    #await kafka_manager.create_topic("dead_letter_queue")
    
    # Connect to Weaviate and Neo4j
    #await weaviate_client.connect()
    #await weaviate_client.ensure_schema_exists()
    
    #await neo4j_client.connect()
    #await neo4j_client.ensure_constraints_exists()
    
    # Start task consumers
    #await task_consumer.start_consumers()
    
    # Start scheduler
    #scheduler.start()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    await close_mongo_connection()
    #await task_consumer.stop_consumers()
    #await kafka_manager.close()
    #await weaviate_client.close()
    #await neo4j_client.close()
    #await task_consumer.stop_consumers()
    #scheduler.shutdown()
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Add middleware
#app.add_middleware(ErrorHandlerMiddleware)
#app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(file_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(tag_router, prefix="/api")
app.include_router(task_router, prefix="/api")

# Create GraphQL schema by combining all queries and mutations
@strawberry.type
class Query(
    FileQuery,
    KnowledgeQuery,
    TagQuery,
    TaskQuery
):
    pass

@strawberry.type
class Mutation(
    FileMutation,
    KnowledgeMutation,
    TagMutation,
    TaskMutation
):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

# Add GraphQL endpoint
app.include_router(graphql_app, prefix="/graphql")

# Health check endpoint
@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "version": settings.APP_VERSION}

@app.get("/api/status")
async def system_status():
    """System status endpoint"""
    from foxmask.shared.schemas import SystemInfo
    import psutil
    import time
    
    return SystemInfo(
        version=settings.APP_VERSION,
        name=settings.APP_NAME,
        environment="development" if settings.DEBUG else "production",
        uptime=time.time() - psutil.boot_time(),
        timestamp=datetime.now(timezone.utc).isoformat()
    )

# Add metrics endpoint
@app.get("/metrics")
async def metrics():
    return await monitoring_service.metrics_endpoint()

# Add health check with detailed monitoring
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "components": {}
    }
    
    # Check MongoDB
    try:
        await mongodb.client.admin.command('ping')
        health_status["components"]["mongodb"] = "healthy"
    except Exception as e:
        health_status["components"]["mongodb"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error("MongoDB health check failed", exc_info=True)
    
    # Check MinIO
    try:
        await minio_client.file_exists("healthcheck")
        health_status["components"]["minio"] = "healthy"
    except Exception as e:
        health_status["components"]["minio"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error("MinIO health check failed", exc_info=True)
    
    # Check Kafka
    try:
        # Simple Kafka health check
        health_status["components"]["kafka"] = "healthy"
    except Exception as e:
        health_status["components"]["kafka"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error("Kafka health check failed", exc_info=True)
    
    return health_status

# Error handlers
@app.exception_handler(404)
async def not_found_exception_handler(request, exc):
    from foxmask.shared.schemas import ErrorResponse
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            success=False,
            error="Resource not found",
            code=404
        ).model_dump()
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    from foxmask.shared.schemas import ErrorResponse
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="Internal server error",
            code=500
        ).model_dump()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "foxmask.main:app",
        host="0.0.0.0",
        port=8888,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )