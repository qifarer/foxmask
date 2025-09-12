# -*- coding: utf-8 -*-
# Knowledge graph service for managing knowledge items and relationships in Neo4j

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from foxmask.core.logger import logger
from foxmask.utils.neo4j_client import neo4j_client, Neo4jLabel, Neo4jRelationship

class KnowledgeGraphService:
    async def create_knowledge_item_node(self, knowledge_item: Dict[str, Any]) -> Optional[str]:
        """Create a knowledge item node in Neo4j"""
        try:
            properties = {
                "id": knowledge_item["id"],
                "uuid": str(uuid.uuid4()),
                "title": knowledge_item.get("title", ""),
                "description": knowledge_item.get("description", ""),
                "type": knowledge_item.get("type", ""),
                "status": knowledge_item.get("status", ""),
                "category": knowledge_item.get("category", ""),
                "createdAt": knowledge_item.get("created_at", datetime.utcnow()).isoformat(),
                "updatedAt": knowledge_item.get("updated_at", datetime.utcnow()).isoformat()
            }
            
            node_id = await neo4j_client.create_node(
                label=Neo4jLabel.KNOWLEDGE_ITEM,
                properties=properties,
                unique_id=knowledge_item["id"]
            )
            
            if node_id:
                # Create relationships
                await self._create_knowledge_item_relationships(knowledge_item)
            
            return node_id
            
        except Exception as e:
            logger.error(f"Error creating knowledge item node: {e}")
            return None

    async def _create_knowledge_item_relationships(self, knowledge_item: Dict[str, Any]):
        """Create relationships for a knowledge item"""
        item_id = knowledge_item["id"]
        created_by = knowledge_item.get("created_by")
        knowledge_base_ids = knowledge_item.get("knowledge_base_ids", [])
        tags = knowledge_item.get("tags", [])
        
        # Link to creator
        if created_by:
            await neo4j_client.create_relationship(
                from_label=Neo4jLabel.USER,
                from_id=created_by,
                to_label=Neo4jLabel.KNOWLEDGE_ITEM,
                to_id=item_id,
                relationship_type=Neo4jRelationship.CREATED_BY
            )
        
        # Link to knowledge bases
        for kb_id in knowledge_base_ids:
            await neo4j_client.create_relationship(
                from_label=Neo4jLabel.KNOWLEDGE_ITEM,
                from_id=item_id,
                to_label=Neo4jLabel.KNOWLEDGE_BASE,
                to_id=kb_id,
                relationship_type=Neo4jRelationship.BELONGS_TO
            )
        
        # Link to tags
        for tag_name in tags:
            # First ensure tag exists
            tag_id = f"tag_{tag_name.lower().replace(' ', '_')}"
            await neo4j_client.create_node(
                label=Neo4jLabel.TAG,
                properties={"id": tag_id, "name": tag_name},
                unique_id=tag_id
            )
            
            await neo4j_client.create_relationship(
                from_label=Neo4jLabel.KNOWLEDGE_ITEM,
                from_id=item_id,
                to_label=Neo4jLabel.TAG,
                to_id=tag_id,
                relationship_type=Neo4jRelationship.TAGGED_WITH
            )

    async def create_knowledge_base_node(self, knowledge_base: Dict[str, Any]) -> Optional[str]:
        """Create a knowledge base node in Neo4j"""
        try:
            properties = {
                "id": knowledge_base["id"],
                "name": knowledge_base.get("name", ""),
                "description": knowledge_base.get("description", ""),
                "isPublic": knowledge_base.get("is_public", False),
                "itemCount": knowledge_base.get("item_count", 0),
                "createdAt": knowledge_base.get("created_at", datetime.utcnow()).isoformat(),
                "updatedAt": knowledge_base.get("updated_at", datetime.utcnow()).isoformat(),
                "createdBy": knowledge_base.get("created_by", "")
            }
            
            node_id = await neo4j_client.create_node(
                label=Neo4jLabel.KNOWLEDGE_BASE,
                properties=properties,
                unique_id=knowledge_base["id"]
            )
            
            return node_id
            
        except Exception as e:
            logger.error(f"Error creating knowledge base node: {e}")
            return None

    async def recommend_related_content(
        self, 
        knowledge_item_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recommend related content based on graph relationships"""
        try:
            recommendations = await neo4j_client.recommend_similar_content(
                knowledge_item_id, limit
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending related content: {e}")
            return []

    async def find_content_path(
        self, 
        start_item_id: str, 
        end_item_id: str, 
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """Find the shortest path between two content items"""
        try:
            query = """
            MATCH path = shortestPath(
                (start:KnowledgeItem {id: $start_id})-[*..$max_depth]-(end:KnowledgeItem {id: $end_id})
            )
            RETURN [node IN nodes(path) | {id: node.id, title: node.title, type: node.type}] AS nodes,
                   [rel IN relationships(path) | type(rel)] AS relationships,
                   length(path) AS pathLength
            """
            
            async with neo4j_client.driver.session() as session:
                result = await session.run(query, {
                    "start_id": start_item_id,
                    "end_id": end_item_id,
                    "max_depth": max_depth
                })
                record = await result.single()
                return record if record else None
                
        except Exception as e:
            logger.error(f"Error finding content path: {e}")
            return None

    async def get_knowledge_graph_insights(self) -> Dict[str, Any]:
        """Get insights from the knowledge graph"""
        try:
            # Get basic statistics
            stats = await neo4j_client.get_knowledge_graph_stats()
            
            # Get most connected nodes
            query = """
            MATCH (n:KnowledgeItem)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, COUNT(r) AS connectionCount
            RETURN n.id AS item_id, 
                   n.title AS title,
                   connectionCount
            ORDER BY connectionCount DESC
            LIMIT 10
            """
            
            async with neo4j_client.driver.session() as session:
                result = await session.run(query)
                popular_items = await result.data()
            
            # Get most used tags
            tag_query = """
            MATCH (t:Tag)
            OPTIONAL MATCH (t)<-[:TAGGED_WITH]-(:KnowledgeItem)
            WITH t, COUNT(*) AS usageCount
            RETURN t.name AS tag_name, usageCount
            ORDER BY usageCount DESC
            LIMIT 10
            """
            
            async with neo4j_client.driver.session() as session:
                result = await session.run(tag_query)
                popular_tags = await result.data()
            
            return {
                "statistics": stats,
                "most_connected_items": popular_items,
                "most_used_tags": popular_tags
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge graph insights: {e}")
            return {}

    async def export_knowledge_graph(self, format: str = "cypher") -> Optional[str]:
        """Export the knowledge graph in various formats"""
        try:
            if format == "cypher":
                # Export as Cypher queries
                query = """
                CALL apoc.export.cypher.all(null, {
                    format: 'cypher-shell',
                    useOptimizations: {type: 'UNWIND_BATCH', unwindBatchSize: 100}
                })
                YIELD file, source, format, nodes, relationships, properties, time
                RETURN file, nodes, relationships, time
                """
                
                async with neo4j_client.driver.session() as session:
                    result = await session.run(query)
                    record = await result.single()
                    return record["file"] if record else None
                    
            else:
                logger.warning(f"Unsupported export format: {format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting knowledge graph: {e}")
            return None

# Global knowledge graph service instance
knowledge_graph_service = KnowledgeGraphService()