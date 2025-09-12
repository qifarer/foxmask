# -*- coding: utf-8 -*-
# foxmask/task/services.py
# Service layer for task management

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from foxmask.core.logger import logger
from foxmask.core.kafka import kafka_manager
from foxmask.core.config import settings
from .models import Task, TaskStatus, TaskType, TaskPriority
from .schemas import TaskCreate


class TaskService:
    async def create_task(self, task_data: TaskCreate, user_id: Optional[str] = None) -> Task:
        """Create a new task"""
        try:
            task = Task(
                **task_data.model_dump(),
                created_by=user_id
            )
            
            await task.insert()
            logger.info(f"Task created: {task.type} by user {user_id}")
            
            # Send to Kafka if it's a high priority task or needs immediate processing
            if task.priority in [TaskPriority.HIGH, TaskPriority.CRITICAL] or not task.scheduled_for:
                await self._send_to_kafka(task)
            
            return task
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create task: {e}"
            )

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return await Task.get(task_id)

    async def update_task(
        self, 
        task_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[Task]:
        """Update task"""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(task, field):
                setattr(task, field, value)
        
        task.update_timestamp()
        await task.save()
        
        logger.info(f"Task updated: {task_id}")
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        task = await self.get_task(task_id)
        if not task:
            return False
        
        await task.delete()
        logger.info(f"Task deleted: {task_id}")
        return True

    async def process_task(self, task_id: str, processor_func) -> bool:
        """Process a task with the given processor function"""
        task = await self.get_task(task_id)
        if not task:
            return False
        
        try:
            task.start_processing()
            await task.save()
            
            # Process the task
            result = await processor_func(task.payload)
            
            task.complete(result)
            await task.save()
            
            logger.info(f"Task completed successfully: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            task.fail(str(e))
            await task.save()
            return False

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            logger.warning(f"Task {task_id} has reached maximum retry attempts")
            return False
        
        task.retry()
        await task.save()
        
        # Send to Kafka for reprocessing
        await self._send_to_kafka(task)
        
        logger.info(f"Task retried: {task_id}, attempt {task.retry_count}")
        return True

    async def get_pending_tasks(
        self, 
        task_type: Optional[TaskType] = None,
        limit: int = 10
    ) -> List[Task]:
        """Get pending tasks ready for processing"""
        query = {"status": TaskStatus.PENDING}
        if task_type:
            query["type"] = task_type
        
        return await Task.find(query).limit(limit).to_list()

    async def get_task_stats(self) -> Dict[str, Any]:
        """Get task statistics"""
        stats = {
            "total_tasks": await Task.find().count(),
            "pending_tasks": await Task.find({"status": TaskStatus.PENDING}).count(),
            "processing_tasks": await Task.find({"status": TaskStatus.PROCESSING}).count(),
            "completed_tasks": await Task.find({"status": TaskStatus.COMPLETED}).count(),
            "failed_tasks": await Task.find({"status": TaskStatus.FAILED}).count(),
        }
        
        # Calculate average processing time for completed tasks
        completed_tasks = await Task.find({"status": TaskStatus.COMPLETED}).to_list()
        if completed_tasks:
            total_time = 0
            count = 0
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    processing_time = (task.completed_at - task.started_at).total_seconds()
                    total_time += processing_time
                    count += 1
            
            if count > 0:
                stats["average_processing_time"] = total_time / count
        
        return stats

    async def search_tasks(
        self, 
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        skip: int = 0, 
        limit: int = 10
    ) -> List[Task]:
        """Search tasks with filters"""
        query = {}
        if task_type:
            query["type"] = task_type
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        
        return await Task.find(query).skip(skip).limit(limit).to_list()

    async def _send_to_kafka(self, task: Task):
        """Send task to Kafka for processing"""
        message = {
            "task_id": str(task.id),
            "type": task.type,
            "payload": task.payload
        }
        
        try:
            await kafka_manager.send_message(f"tasks_{task.type}", message)
            logger.info(f"Task sent to Kafka: {task.id}")
        except Exception as e:
            logger.error(f"Failed to send task to Kafka: {e}")

task_service = TaskService()