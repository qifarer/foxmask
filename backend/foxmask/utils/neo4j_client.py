# -*- coding: utf-8 -*-
# Neo4j client utilitys

from neo4j import AsyncGraphDatabase, AsyncSession
from typing import Optional, Dict, List, Any, Union
import json
from datetime import datetime
from enum import Enum
import asyncio

from foxmask.core.config import settings
from foxmask.core.logger import logger

class Neo4jLabel(str, Enum):
    """Neo4j node labels"""
    KNOWLEDGE_ITEM = "KnowledgeItem"
    KNOWLEDGE_BASE = "KnowledgeBase"
    USER = "User"
    TAG = "Tag"
    FILE = "File"
    ORGANIZATION = "Organization"

class Neo4jRelationship(str, Enum):
    """Neo4j relationship types"""
    CONTAINS = "CONTAINS"
    CREATED_BY = "CREATED_BY"
    TAGGED_WITH = "TAGGED_WITH"
    RELATED_TO = "RELATED_TO"
    BELONGS_TO = "BELONGS_TO"
    REFERENCES = "REFERENCES"
    SIMILAR_TO = "SIMILAR_TO"

class Neo4jClient:
    def __init__(self):
        self.driver: Optional[AsyncGraphDatabase] = None
        self.connected = False
        self.session: Optional[AsyncSession] = None

    async def connect(self):
        """Connect to Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=10,
                connection_acquisition_timeout=30,
                connection_timeout=30,
                max_connection_lifetime=3600
            )
            
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            
            self.connected = True
            logger.info("Connected to Neo4j successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.connected = False
            raise

    async def ensure_constraints_exist(self):
        """Ensure Neo4j constraints and indexes exist"""
        if not self.connected:
            await self.connect()
        
        try:
            async with self.driver.session() as session:
                # Create constraints for uniqueness
                constraints = [
                    # Knowledge items
                    "CREATE CONSTRAINT knowledge_item_id IF NOT EXISTS FOR (n:KnowledgeItem) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT knowledge_item_uuid IF NOT EXISTS FOR (n:KnowledgeItem) REQUIRE n.uuid IS UNIQUE",
                    
                    # Knowledge bases
                    "CREATE CONSTRAINT knowledge_base_id IF NOT EXISTS FOR (n:KnowledgeBase) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT knowledge_base_name IF NOT EXISTS FOR (n:KnowledgeBase) REQUIRE n.name IS UNIQUE",
                    
                    # Users
                    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (n:User) REQUIRE n.email IS UNIQUE",
                    
                    # Tags
                    "CREATE CONSTRAINT tag_id IF NOT EXISTS FOR (n:Tag) REQUIRE n.id IS UNIQUE",
                    "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (n:Tag) REQUIRE n.name IS UNIQUE",
                    
                    # Files
                    "CREATE CONSTRAINT file_id IF NOT EXISTS FOR (n:File) REQUIRE n.id IS UNIQUE"
                ]
                
                for constraint in constraints:
                    await session.run(constraint)
                
                # Create indexes for better performance
                indexes = [
                    # Index for knowledge item titles
                    "CREATE INDEX knowledge_item_title IF NOT EXISTS FOR (n:KnowledgeItem) ON (n.title)",
                    
                    # Index for knowledge item types
                    "CREATE INDEX knowledge_item_type IF NOT EXISTS FOR (n:KnowledgeItem) ON (n.type)",
                    
                    # Index for knowledge item status
                    "CREATE INDEX knowledge_item_status IF NOT EXISTS FOR (n:KnowledgeItem) ON (n.status)",
                    
                    # Index for created dates
                    "CREATE INDEX knowledge_item_created_at IF NOT EXISTS FOR (n:KnowledgeItem) ON (n.createdAt)",
                    
                    # Index for tags
                    "CREATE INDEX tag_usage_count IF NOT EXISTS FOR (n:Tag) ON (n.usageCount)"
                ]
                
                for index in indexes:
                    await session.run(index)
                
                logger.info("Neo4j constraints and indexes ensured")
                
        except Exception as e:
            logger.error(f"Error ensuring Neo4j constraints: {e}")
            raise

    async def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute a Cypher query and return results"""
        if not self.connected:
            await self.connect()
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Error executing Neo4j query: {e}")
            return []

    async def create_node(
        self, 
        label: str, 
        properties: Dict[str, Any],
        unique_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a node in Neo4j"""
        if not self.connected:
            await self.connect()
        
        try:
            if unique_id:
                # Use MERGE to ensure uniqueness
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $properties
                RETURN n.id as node_id
                """
                parameters = {"id": unique_id, "properties": properties}
            else:
                # Create new node
                query = f"""
                CREATE (n:{label} $properties)
                RETURN n.id as node_id
                """
                parameters = {"properties": properties}
            
            async with self.driver.session() as session:
                result = await session.run(query, parameters)
                record = await result.single()
                return record["node_id"] if record else None
                
        except Exception as e:
            logger.error(f"Error creating Neo4j node: {e}")
            return None

    async def get_node(self, label: str, node_id: str) -> Optional[Dict]:
        """Get a node by ID"""
        if not self.connected:
            await self.connect()
        
        try:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            RETURN n
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {"node_id": node_id})
                record = await result.single()
                return dict(record["n"]) if record else None
                
        except Exception as e:
            logger.error(f"Error getting Neo4j node: {e}")
            return None

    async def update_node(
        self, 
        label: str, 
        node_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """Update a node's properties"""
        if not self.connected:
            await self.connect()
        
        try:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            SET n += $properties
            RETURN n.id as node_id
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {"node_id": node_id, "properties": properties})
                record = await result.single()
                return record is not None
                
        except Exception as e:
            logger.error(f"Error updating Neo4j node: {e}")
            return False

    async def delete_node(self, label: str, node_id: str) -> bool:
        """Delete a node and its relationships"""
        if not self.connected:
            await self.connect()
        
        try:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            DETACH DELETE n
            """
            
            async with self.driver.session() as session:
                await session.run(query, {"node_id": node_id})
                return True
                
        except Exception as e:
            logger.error(f"Error deleting Neo4j node: {e}")
            return False

    async def create_relationship(
        self, 
        from_label: str, 
        from_id: str, 
        to_label: str, 
        to_id: str, 
        relationship_type: str,
        properties: Optional[Dict] = None
    ) -> bool:
        """Create a relationship between two nodes"""
        if not self.connected:
            await self.connect()
        
        try:
            query = f"""
            MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}})
            MERGE (a)-[r:{relationship_type}]->(b)
            {f"SET r += $properties" if properties else ""}
            RETURN type(r) as relationship_type
            """
            
            parameters = {"from_id": from_id, "to_id": to_id}
            if properties:
                parameters["properties"] = properties
            
            async with self.driver.session() as session:
                result = await session.run(query, parameters)
                record = await result.single()
                return record is not None
                
        except Exception as e:
            logger.error(f"Error creating Neo4j relationship: {e}")
            return False

    async def delete_relationship(
        self, 
        from_label: str, 
        from_id: str, 
        to_label: str, 
        to_id: str, 
        relationship_type: str
    ) -> bool:
        """Delete a relationship between two nodes"""
        if not self.connected:
            await self.connect()
        
        try:
            query = f"""
            MATCH (a:{from_label} {{id: $from_id}})-[r:{relationship_type}]->(b:{to_label} {{id: $to_id}})
            DELETE r
            """
            
            async with self.driver.session() as session:
                await session.run(query, {"from_id": from_id, "to_id": to_id})
                return True
                
        except Exception as e:
            logger.error(f"Error deleting Neo4j relationship: {e}")
            return False

    async def find_related_nodes(
        self, 
        node_id: str, 
        label: str,
        relationship_type: Optional[str] = None,
        direction: str = "BOTH",
        depth: int = 1,
        limit: int = 50
    ) -> List[Dict]:
        """Find nodes related to a given node"""
        if not self.connected:
            await self.connect()
        
        try:
            relationship_pattern = ""
            if relationship_type:
                if direction == "OUTGOING":
                    relationship_pattern = f"-[:{relationship_type}*1..{depth}]->"
                elif direction == "INCOMING":
                    relationship_pattern = f"<-[:{relationship_type}*1..{depth}]-"
                else:
                    relationship_pattern = f"-[:{relationship_type}*1..{depth}]-"
            else:
                if direction == "OUTGOING":
                    relationship_pattern = f"-[*1..{depth}]->"
                elif direction == "INCOMING":
                    relationship_pattern = f"<-[*1..{depth}]-"
                else:
                    relationship_pattern = f"-[*1..{depth}]-"
            
            query = f"""
            MATCH (start:{label} {{id: $node_id}}){relationship_pattern}(related)
            RETURN related, 
                   [r IN relationships(path) | type(r)] as relationship_types,
                   length(path) as distance
            LIMIT $limit
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {"node_id": node_id, "limit": limit})
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Error finding related nodes: {e}")
            return []

    async def recommend_similar_content(
        self, 
        knowledge_item_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Recommend similar content based on graph relationships"""
        if not self.connected:
            await self.connect()
        
        try:
            query = """
            MATCH (source:KnowledgeItem {id: $knowledge_item_id})
            MATCH (source)-[:TAGGED_WITH]->(tag:Tag)<-[:TAGGED_WITH]-(similar:KnowledgeItem)
            WHERE similar.id <> source.id
            WITH similar, COUNT(tag) AS commonTags
            MATCH (source)-[:BELONGS_TO]->(kb:KnowledgeBase)<-[:BELONGS_TO]-(similar)
            WITH similar, commonTags, COUNT(kb) AS commonBases
            RETURN similar.id AS item_id, 
                   similar.title AS title,
                   similar.description AS description,
                   commonTags,
                   commonBases,
                   (commonTags * 2 + commonBases) AS similarityScore
            ORDER BY similarityScore DESC
            LIMIT $limit
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "knowledge_item_id": knowledge_item_id,
                    "limit": limit
                })
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Error recommending similar content: {e}")
            return []

    async def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        if not self.connected:
            await self.connect()
        
        try:
            queries = {
                "total_nodes": "MATCH (n) RETURN COUNT(n) AS count",
                "total_relationships": "MATCH ()-[r]->() RETURN COUNT(r) AS count",
                "knowledge_items": "MATCH (n:KnowledgeItem) RETURN COUNT(n) AS count",
                "knowledge_bases": "MATCH (n:KnowledgeBase) RETURN COUNT(n) AS count",
                "users": "MATCH (n:User) RETURN COUNT(n) AS count",
                "tags": "MATCH (n:Tag) RETURN COUNT(n) AS count",
                "files": "MATCH (n:File) RETURN COUNT(n) AS count"
            }
            
            stats = {}
            async with self.driver.session() as session:
                for key, query in queries.items():
                    result = await session.run(query)
                    record = await result.single()
                    stats[key] = record["count"] if record else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting knowledge graph stats: {e}")
            return {}

    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            self.connected = False
            logger.info("Neo4j connection closed")

# Global Neo4j client instance
neo4j_client = Neo4jClient()