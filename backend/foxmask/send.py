# -*- coding: utf-8 -*-
# foxmask/file/graphql_client.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# GraphQL client for chunked file upload

import aiohttp
import asyncio
import hashlib
import os
from typing import Dict, Any, Optional
import json
import base64
from pathlib import Path
from foxmask.core.kafka import kafka_manager
from foxmask.task.message import (
    MessageTopicEnum,
    MessageEventTypeEnum,
    KnowledgeProcessingMessage
)    
# Usage example
async def main():
    # Replace with your actual token
    # 触发进一步处理
    uids=[
        'abac87ac-5f26-4e0e-a14d-feee9e90d784',
        "6556dab4-9263-4045-8ee0-2c1b247daf4b",
        "334b3fbc-ae5f-4415-8a61-897c27e75689",
        "d6c1a2cd-5224-43b0-a96b-4f099e7bb827",
        "6a2d57f3-683d-402f-a9cc-52079565e06d"]


    for uid in uids:
        tenant_id="foxmask"
        processing_message = {
            "type": MessageEventTypeEnum.PARSE_MD_FROM_SOURCE.value,
            "item_id": str(uid),
            "tenant_id": tenant_id
        }
        
        await kafka_manager.send_message(
            topic=MessageTopicEnum.KB_PROCESSING,
            value=processing_message,
            key=str(uid)
        )
            
if __name__ == "__main__":
    asyncio.run(main())