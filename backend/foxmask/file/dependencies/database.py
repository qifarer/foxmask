from fastapi import Depends
from ..services.file import FileService
from ..services.mongo import mongo_service

async def get_file_service() -> FileService:
    return FileService()

async def get_mongo_service():
    return mongo_service