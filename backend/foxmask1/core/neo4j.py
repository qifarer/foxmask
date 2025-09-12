from neo4j import GraphDatabase
from foxmask.core.config import get_settings

settings = get_settings()

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    async def create_knowledge_node(self, item_id: str, content: dict, knowledge_type: str = None) -> str:
        with self.driver.session() as session:
            # 创建知识节点
            query = """
            CREATE (k:KnowledgeItem {
                id: $item_id,
                title: $title,
                description: $description,
                type: $type,
                createdAt: datetime()
            })
            RETURN elementId(k) as node_id
            """
            
            result = session.run(
                query,
                item_id=item_id,
                title=content.get("title", ""),
                description=content.get("description", ""),
                type=knowledge_type
            )
            
            node_id = result.single()["node_id"]
            
            # 如果内容中有实体，创建关系
            entities = content.get("entities", [])
            for entity in entities:
                await self._create_entity_relationship(session, node_id, entity)
            
            return node_id
    
    async def _create_entity_relationship(self, session, node_id: str, entity: dict):
        # 创建实体节点（如果不存在）
        entity_query = """
        MERGE (e:Entity {name: $name, type: $type})
        ON CREATE SET e.createdAt = datetime()
        RETURN elementId(e) as entity_id
        """
        
        entity_result = session.run(
            entity_query,
            name=entity.get("name"),
            type=entity.get("type", "unknown")
        )
        entity_id = entity_result.single()["entity_id"]
        
        # 创建关系
        relationship_query = """
        MATCH (k:KnowledgeItem) WHERE elementId(k) = $node_id
        MATCH (e:Entity) WHERE elementId(e) = $entity_id
        MERGE (k)-[r:MENTIONS]->(e)
        SET r.relationship = $relationship, r.confidence = $confidence
        """
        
        session.run(
            relationship_query,
            node_id=node_id,
            entity_id=entity_id,
            relationship=entity.get("relationship", "mentions"),
            confidence=entity.get("confidence", 1.0)
        )
    
    async def delete_knowledge_node(self, node_id: str):
        with self.driver.session() as session:
            query = """
            MATCH (k:KnowledgeItem) WHERE elementId(k) = $node_id
            DETACH DELETE k
            """
            session.run(query, node_id=node_id)
    
    async def close(self):
        self.driver.close()

# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()