# foxmask/task/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from foxmask.auth.dependencies import get_current_user
from foxmask.auth.schemas import User
from foxmask.task.services import TaskService
from foxmask.task.schemas import TaskResponse
from foxmask.task.models import TaskType, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    document_id: Optional[str] = None,
    task_type: Optional[TaskType] = None,
    task_status: Optional[TaskStatus] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    service = TaskService()
    tasks = await service.list_tasks(
        current_user.id, 
        document_id, 
        task_type,
        task_status,
        skip, 
        limit
    )
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    service = TaskService()
    task = await service.get_task(task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task