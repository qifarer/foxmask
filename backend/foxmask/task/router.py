# -*- coding: utf-8 -*-
# foxmask/task/router.py
# API router for task management and Kafka operations

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List

from foxmask.shared.dependencies import require_admin, get_api_context
from foxmask.task.services import task_service
from foxmask.task.producers import task_producer
from foxmask.task.consumers import task_consumer
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/kafka/stats")
async def get_kafka_stats(
    request: Request,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Get Kafka statistics (admin only)"""
    try:
        # Get consumer group statistics
        consumer_stats = {}
        for group_id in task_consumer.consumers.keys():
            stats = await task_consumer.get_consumer_stats(group_id)
            if stats:
                consumer_stats[group_id] = stats
        
        # Get topic metadata (simplified)
        topics_metadata = {}
        for topic in [settings.KAFKA_KNOWLEDGE_TOPIC, "file_processing", "notifications"]:
            metadata = await kafka_manager.get_topic_metadata(topic)
            if metadata:
                topics_metadata[topic] = metadata
        
        return {
            "consumer_groups": consumer_stats,
            "topics": topics_metadata,
            "producer_connected": kafka_manager.producer is not None,
            "consumers_running": task_consumer.running,
            "api_key_info": {
                "api_key_id": api_key_info["api_key_id"],
                "user_id": api_key_info["casdoor_user_id"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Kafka stats: {e}"
        )

@router.post("/kafka/consumers/restart")
async def restart_kafka_consumers(
    request: Request,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Restart Kafka consumers (admin only)"""
    try:
        await task_consumer.stop_consumers()
        await asyncio.sleep(1)  # Brief delay
        await task_consumer.start_consumers()
        
        return {
            "message": "Kafka consumers restarted successfully",
            "api_key_id": api_key_info["api_key_id"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart consumers: {e}"
        )

@router.get("/kafka/messages/produced")
async def get_produced_messages_stats(
    request: Request,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Get produced messages statistics (admin only)"""
    try:
        # Get actual statistics from producer if available
        actual_stats = {}
        if hasattr(task_producer, 'get_production_stats'):
            actual_stats = await task_producer.get_production_stats()
        else:
            # Fallback to service-based statistics
            actual_stats = await task_service.get_message_production_stats()
        
        return {
            "stats": actual_stats,
            "api_key_id": api_key_info["api_key_id"],
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message statistics: {e}"
        )

@router.post("/test/message")
async def produce_test_message(
    request: Request,
    message_type: str,
    payload: Dict[str, Any],
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Produce a test message (admin only)"""
    try:
        # Add API key context to the payload for tracking
        enhanced_payload = payload.copy()
        enhanced_payload["api_key_id"] = api_key_info["api_key_id"]
        enhanced_payload["user_id"] = api_key_info["casdoor_user_id"]
        
        if message_type == "knowledge_processing":
            message_id = await task_producer.produce_knowledge_processing_task(
                knowledge_item_id=enhanced_payload["knowledge_item_id"],
                process_types=enhanced_payload.get("process_types", ["parse", "vectorize", "graph"]),
                metadata={"api_key_id": api_key_info["api_key_id"]}
            )
        elif message_type == "file_processing":
            message_id = await task_producer.produce_file_processing_task(
                file_id=enhanced_payload["file_id"],
                processing_type=enhanced_payload["processing_type"],
                options=enhanced_payload.get("options", {}),
                metadata={"api_key_id": api_key_info["api_key_id"]}
            )
        elif message_type == "notification":
            message_id = await task_producer.produce_notification_task(
                user_id=enhanced_payload["user_id"],
                message=enhanced_payload["message"],
                notification_type=enhanced_payload.get("notification_type", "info"),
                metadata={"api_key_id": api_key_info["api_key_id"]}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown message type: {message_type}"
            )
        
        return {
            "message": "Test message produced successfully",
            "message_id": message_id,
            "message_type": message_type,
            "api_key_id": api_key_info["api_key_id"],
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required field: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to produce test message: {e}"
        )

@router.get("/consumer/status")
async def get_consumer_status(
    request: Request,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Get consumer status information (admin only)"""
    try:
        status_info = {
            "running": task_consumer.running,
            "consumer_count": len(task_consumer.consumers),
            "topics_subscribed": list(task_consumer.consumers.keys()),
            "last_restart": getattr(task_consumer, 'last_restart_time', None),
            "api_key_id": api_key_info["api_key_id"]
        }
        
        # Add detailed consumer information if available
        if hasattr(task_consumer, 'get_detailed_status'):
            detailed_status = await task_consumer.get_detailed_status()
            status_info["detailed_status"] = detailed_status
        
        return status_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consumer status: {e}"
        )

@router.post("/consumer/{group_id}/pause")
async def pause_consumer_group(
    request: Request,
    group_id: str,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Pause a specific consumer group (admin only)"""
    try:
        if group_id not in task_consumer.consumers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consumer group {group_id} not found"
            )
        
        success = await task_consumer.pause_consumer(group_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to pause consumer group {group_id}"
            )
        
        return {
            "message": f"Consumer group {group_id} paused successfully",
            "group_id": group_id,
            "api_key_id": api_key_info["api_key_id"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause consumer: {e}"
        )

@router.post("/consumer/{group_id}/resume")
async def resume_consumer_group(
    request: Request,
    group_id: str,
    api_key_info: dict = Depends(require_admin)
) -> Dict[str, Any]:
    """Resume a specific consumer group (admin only)"""
    try:
        if group_id not in task_consumer.consumers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consumer group {group_id} not found"
            )
        
        success = await task_consumer.resume_consumer(group_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to resume consumer group {group_id}"
            )
        
        return {
            "message": f"Consumer group {group_id} resumed successfully",
            "group_id": group_id,
            "api_key_id": api_key_info["api_key_id"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume consumer: {e}"
        )

@router.get("/api-key/info")
async def get_api_key_info(
    request: Request,
    api_key_info: dict = Depends(get_api_context)
) -> Dict[str, Any]:
    """Get information about the current API key"""
    return {
        "api_key_info": api_key_info,
        "permissions": api_key_info.get("permissions", []),
        "has_admin_access": "admin" in api_key_info.get("permissions", [])
    }