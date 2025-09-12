from knowledge.service import knowledge_item_service
from knowledge.model import ItemStatus, SourceType, KnowledgeType
from core.minio_client import minio_client
from core.weaviate_client import weaviate_client
from core.neo4j_client import neo4j_client
from file.utils import FileParser
from knowledge.utils import WebCrawler
from bson import ObjectId

async def handle_knowledge_item_created(message):
    item_id = message['item_id']
    source_type = message['source_type']
    knowledge_type = message['knowledge_type']
    sources = message['sources']
    
    # 更新状态为解析中
    await knowledge_item_service.update_item_status(ObjectId(item_id), ItemStatus.PARSING)
    
    try:
        parsed_content = None
        
        # 根据源类型处理内容
        if source_type == "file":
            parser = FileParser()
            parsed_content = await parser.parse_files(sources, KnowledgeType(knowledge_type))
        elif source_type == "webpage":
            crawler = WebCrawler()
            parsed_content = await crawler.crawl_pages(sources)
        elif source_type == "api":
            parsed_content = await process_api_data(sources)
        elif source_type == "chat":
            parsed_content = await process_chat_data(sources)
        elif source_type == "structured":
            parsed_content = await process_structured_data(sources)
        elif source_type in ["product", "brand"]:
            parsed_content = await process_commercial_data(sources, source_type)
        
        if parsed_content:
            # 存储到MinIO
            md_ref, json_ref = await minio_client.store_content(item_id, parsed_content)
            
            # 更新知识条目引用
            item = await knowledge_item_service.get_item(ObjectId(item_id))
            item.content_md_ref = md_ref
            item.content_json_ref = json_ref
            item.update_timestamp()
            await item.save()
            
            # 发送解析完成消息
            from task.producer import send_knowledge_item_parsed
            await send_knowledge_item_parsed(item_id, md_ref, json_ref)
        else:
            raise Exception("Failed to parse content from sources")
        
    except Exception as e:
        await knowledge_item_service.update_item_status(
            ObjectId(item_id), 
            ItemStatus.ERROR, 
            f"Parsing failed: {str(e)}"
        )

async def handle_knowledge_item_parsed(message):
    item_id = message['item_id']
    json_ref = message['json_ref']
    
    # 更新状态为向量化中
    await knowledge_item_service.update_item_status(ObjectId(item_id), ItemStatus.VECTORIZING)
    
    try:
        # 从MinIO获取JSON内容
        content = await minio_client.get_content(json_ref)
        
        # 向量化并存储到Weaviate
        vector_id = await weaviate_client.vectorize_content(item_id, content)
        
        # 更新知识条目向量ID
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        item.vector_id = vector_id
        item.update_timestamp()
        await item.save()
        
        # 发送向量化完成消息
        from task.producer import send_knowledge_item_vectorized
        await send_knowledge_item_vectorized(item_id, vector_id)
        
    except Exception as e:
        await knowledge_item_service.update_item_status(
            ObjectId(item_id), 
            ItemStatus.ERROR, 
            f"Vectorization failed: {str(e)}"
        )

async def handle_knowledge_item_vectorized(message):
    item_id = message['item_id']
    
    # 更新状态为图谱处理中
    await knowledge_item_service.update_item_status(ObjectId(item_id), ItemStatus.GRAPH_PROCESSING)
    
    try:
        # 获取知识条目
        item = await knowledge_item_service.get_item(ObjectId(item_id))
        
        # 从MinIO获取JSON内容
        content = await minio_client.get_content(item.content_json_ref)
        
        # 创建图谱节点和关系
        graph_id = await neo4j_client.create_knowledge_node(item_id, content, item.knowledge_type.value)
        
        # 更新知识条目图谱ID
        item.graph_id = graph_id
        item.status = ItemStatus.COMPLETED
        item.update_timestamp()
        await item.save()
        
    except Exception as e:
        await knowledge_item_service.update_item_status(
            ObjectId(item_id), 
            ItemStatus.ERROR, 
            f"Graph processing failed: {str(e)}"
        )

# 辅助方法
async def process_api_data(sources):
    return {"content": f"API data from {sources}", "title": "API Data"}

async def process_chat_data(sources):
    return {"content": f"Chat data from {sources}", "title": "Chat Data"}

async def process_structured_data(sources):
    return {"content": f"Structured data from {sources}", "title": "Structured Data"}

async def process_commercial_data(sources, source_type):
    return {"content": f"{source_type} data from {sources}", "title": f"{source_type.capitalize()} Data"}