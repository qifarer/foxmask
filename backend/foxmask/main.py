# app/main.py (更新版)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter
from contextlib import asynccontextmanager
from foxmask.core.config import get_settings
from foxmask.core.database import connect_to_mongo, close_mongo_connection
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.routers import router as auth_router
from foxmask.file.routers import router as file_router
from foxmask.document.routers import router as document_router
from foxmask.task.routers import router as task_router
from foxmask.tracking.routers import router as tracking_router
from foxmask.middleware.tracking_middleware import TrackingMiddleware

# Import GraphQL schemas
from foxmask.file.graphql import FileQuery, FileMutation
from foxmask.document.graphql import DocumentQuery, DocumentMutation

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    # Start background tasks like Kafka consumers here
    yield
    # Shutdown
    await close_mongo_connection()

# Create GraphQL schema
@strawberry.type
class Query(FileQuery, DocumentQuery):
    pass

@strawberry.type
class Mutation(FileMutation, DocumentMutation):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Create GraphQL router
graphql_app = GraphQLRouter(
    schema,
    context_getter=lambda: {"user": get_current_user()}
)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add tracking middleware
app.add_middleware(TrackingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(file_router, prefix=settings.API_V1_STR)
app.include_router(document_router, prefix=settings.API_V1_STR)
app.include_router(task_router, prefix=settings.API_V1_STR)
app.include_router(tracking_router, prefix=settings.API_V1_STR)

# Include GraphQL
app.include_router(graphql_app, prefix=settings.GRAPHQL_STR)

@app.get("/")
async def root():
    return {"message": "Welcome to Foxmask Document Management System"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )