from foxmask.core.kafka import kafka_producer

async def send_knowledge_item_created(item_id: str, source_type: str, knowledge_type: str, sources: list):
    await kafka_producer.send_message("knowledge-item-created", {
        "item_id": item_id,
        "source_type": source_type,
        "knowledge_type": knowledge_type,
        "sources": sources
    })

async def send_knowledge_item_parsed(item_id: str, md_ref: str, json_ref: str):
    await kafka_producer.send_message("knowledge-item-parsed", {
        "item_id": item_id,
        "md_ref": md_ref,
        "json_ref": json_ref
    })

async def send_knowledge_item_vectorized(item_id: str, vector_id: str):
    await kafka_producer.send_message("knowledge-item-vectorized", {
        "item_id": item_id,
        "vector_id": vector_id
    })