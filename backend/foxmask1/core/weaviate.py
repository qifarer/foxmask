import weaviate
from weaviate import Client
from foxmask.core.config import get_settings

settings = get_settings()

class WeaviateClient:
    def __init__(self):
        auth_config = None
        if settings.WEAVIATE_API_KEY:
            auth_config = weaviate.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
        
        self.client = Client(
            url=settings.WEAVIATE_URL,
            auth_client_secret=auth_config
        )
    
    async def vectorize_content(self, item_id: str, content: dict) -> str:
        # 创建或获取类
        if not self.client.schema.exists("KnowledgeItem"):
            class_obj = {
                "class": "KnowledgeItem",
                "properties": [
                    {
                        "name": "itemId",
                        "dataType": ["string"]
                    },
                    {
                        "name": "title",
                        "dataType": ["string"]
                    },
                    {
                        "name": "description",
                        "dataType": ["string"]
                    },
                    {
                        "name": "content",
                        "dataType": ["text"]
                    }
                ]
            }
            self.client.schema.create_class(class_obj)
        
        # 创建向量
        properties = {
            "itemId": item_id,
            "title": content.get("title", ""),
            "description": content.get("description", ""),
            "content": content.get("content", "")
        }
        
        result = self.client.data_object.create(
            data_object=properties,
            class_name="KnowledgeItem"
        )
        
        return result
    
    async def search_similar(self, query: str, limit: int = 10) -> list:
        near_text = {
            "concepts": [query]
        }
        
        result = self.client.query\
            .get("KnowledgeItem", ["itemId", "title", "description", "content"])\
            .with_near_text(near_text)\
            .with_limit(limit)\
            .do()
        
        return result.get("data", {}).get("Get", {}).get("KnowledgeItem", [])
    
    async def delete_vector(self, vector_id: str):
        try:
            self.client.data_object.delete(uuid=vector_id, class_name="KnowledgeItem")
        except Exception as e:
            print(f"Error deleting vector: {e}")

# 全局Weaviate客户端实例
weaviate_client = WeaviateClient()