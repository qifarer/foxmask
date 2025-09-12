# foxmask/file/mongo.py
import logging
from typing import List, Type
from beanie import PydanticObjectId
from foxmask.file.models import File, FileChunk, FileVersion, FileAccessLog
from foxmask.core.mongo import get_mongo_db

logger = logging.getLogger(__name__)

def get_file_models() -> List[Type]:
    return [File, FileChunk, FileVersion, FileAccessLog]

async def init_file_indexes():
    """Create indexes specific to file domain. This uses motor via get_mongo_db.
    You can also rely on Beanie's Settings.indexes; here is an explicit example.
    """
    try:
        db = await get_mongo_db()
        files = db["files"]
        await files.create_index("file_id", unique=True)
        await files.create_index("filename")
        await files.create_index([("owner_id", 1), ("tenant_id", 1)])
        await files.create_index([("file_type", 1), ("status", 1)])
        await files.create_index("uploaded_at")
        await files.create_index("is_deleted")
        await files.create_index([("filename", "text"), ("tags", "text")])

        chunks = db["file_chunks"]
        await chunks.create_index([("file_id", 1), ("chunk_number", 1)], unique=True)

        versions = db["file_versions"]
        await versions.create_index([("file_id", 1), ("version", 1)], unique=True)

        logs = db["file_access_logs"]
        await logs.create_index([("file_id", 1), ("accessed_at", -1)])
        await logs.create_index("accessed_at", expireAfterSeconds=2592000) # 30 days

        logger.info("File domain indexes created")
    except Exception as e:
        logger.exception("Failed to create file indexes: %s", e)
        raise