# foxmask/task/graphql.py
import strawberry
from typing import List, Optional
from foxmask.task.models import Task, TaskStatus, TaskType
from foxmask.task.services import TaskService
from foxmask.auth.dependencies import get_current_user

@strawberry.type
class Task:
    id: strawberry.ID
    type: str
    status: str
    document_id: str
    owner: str
    created_at: str
    updated_at: str

@strawberry.type
class TaskMutation:
    @strawberry.mutation
    async def create_task(self, info, task_type: str, document_id: str) -> Task:
        user = await get_current_user(info.context["request"])
        service = TaskService()
        task = await service.create_task(
            TaskType(task_type),
            document_id,
            user.id
        )
        return Task(**task.dict())

@strawberry.type
class TaskQuery:
    @strawberry.field
    async def tasks(self, info, document_id: Optional[str] = None) -> List[Task]:
        user = await get_current_user(info.context["request"])
        service = TaskService()
        tasks = await service.list_tasks(user.id, document_id)
        return [Task(**task.dict()) for task in tasks]