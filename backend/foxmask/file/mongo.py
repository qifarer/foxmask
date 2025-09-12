# -*- coding: utf-8 -*-
# foxmask/file/mongo.py
# MongoDB initialization for file metadata using Beanie ODM

from beanie import init_beanie
from .models import File, FileChunk, FileProcessingJob, FileVersion
from foxmask.core.mongo import mongodb

async def init_file_db():
    """Initialize file database"""
    await init_beanie(
        database=mongodb.database,
        document_models=[File, FileChunk, FileProcessingJob, FileVersion],
    )