# foxmask/task/services.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from foxmask.core.database import get_database
from foxmask.core.exceptions import NotFoundError
from foxmask.task.models import Task, TaskStatus, TaskType

class TaskService:
    def __init__(self):
        self.db = get_database()
    
    async def create_task(
        self, 
        task_type: TaskType, 
        document_id: str, 
        owner: str,
        details: Dict[str, Any] = None
    ) -> Task:
        task = Task(
            type=task_type,
            document_id=document_id,
            owner=owner,
            details=details or {}
        )
        
        await self.db.tasks.insert_one(task.dict())
        return task
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        result: Dict[str, Any] = None,
        error: str = None
    ) -> Task:
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if result is not None:
            update_data["result"] = result
        
        if error is not None:
            update_data["error"] = error
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()
        
        await self.db.tasks.update_one(
            {"id": task_id},
            {"$set": update_data}
        )
        
        task_data = await self.db.tasks.find_one({"id": task_id})
        return Task(**task_data)
    
    async def get_task(self, task_id: str, owner: str) -> Optional[Task]:
        data = await self.db.tasks.find_one({"id": task_id, "owner": owner})
        if data:
            return Task(**data)
        return None
    
    async def list_tasks(
        self, 
        owner: str, 
        document_id: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        query = {"owner": owner}
        
        if document_id:
            query["document_id"] = document_id
        
        if task_type:
            query["type"] = task_type
        
        if status:
            query["status"] = status
        
        cursor = self.db.tasks.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return [Task(**doc) async for doc in cursor]