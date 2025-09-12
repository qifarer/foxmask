# foxmask/core/startup.py
import logging
from typing import List, Type

from foxmask.core.mongo import connect_to_mongo, init_beanie_with_models
from foxmask.file.mongo import get_file_models, init_file_indexes

logger = logging.getLogger(__name__)

async def init_mongo_and_domains():
    """Call from application startup. Collect domain models and initialize Beanie.
    Each domain exposes `get_*_models()` and optional `init_*_indexes()`.
    """
    # 1. connect motor client
    await connect_to_mongo()

    # 2. collect domain models
    document_models: List[Type] = []
    document_models.extend(get_file_models())

    # add other domain models in similar way, e.g. auth, tag, ...

    # 3. init beanie with collected models
    await init_beanie_with_models(document_models)

    # 4. let domains create their indexes
    await init_file_indexes()

    logger.info("Mongo and domain initialization finished")