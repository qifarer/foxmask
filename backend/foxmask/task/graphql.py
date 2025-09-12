# -*- coding: utf-8 -*-
# foxmask/task/graphql.py
# GraphQL schema and resolvers for task management
import strawberry
from strawberry.scalars import JSON as JSONScalar
from typing import Optional, List
from .models import Task, TaskStatus, TaskType as TaskTypeModel, TaskPriority
from .schemas import TaskCreate, TaskUpdate
from .services import task_service
from foxmask.shared.dependencies import require_read, require_write, require_admin
from functools import wraps

# API Key context decorator for GraphQL
def api_key_required(permission: str = "read"):
    """Decorator to require API key authentication for GraphQL resolvers"""
    def decorator(resolver):
        @wraps(resolver)
        async def wrapper(*args, **kwargs):
            info = kwargs.get('info') or args[-1] if args else None
            if not info or not hasattr(info, 'context'):
                raise Exception("Authentication required")
            
            request = info.context.get("request")
            if not request:
                raise Exception("Request context not available")
            
            # Use appropriate permission dependency
            if permission == "read":
                api_key_info = await require_read(request)
            elif permission == "write":
                api_key_info = await require_write(request)
            elif permission == "admin":
                api_key_info = await require_admin(request)
            else:
                api_key_info = await require_read(request)
            
            # Store API key info in context for later use
            info.context["api_key_info"] = api_key_info
            return await resolver(*args, **kwargs)
        return wrapper
    return decorator

@strawberry.type
class TaskType:
    """GraphQL task type"""
    id: strawberry.ID
    type: str
    status: str
    priority: str
    payload: JSONScalar
    result: Optional[JSONScalar]
    error: Optional[str]
    retry_count: int
    max_retries: int
    scheduled_for: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_by: Optional[str]
    parent_task_id: Optional[str]
    created_at: str
    updated_at: str

@strawberry.type
class APIKeyInfo:
    """GraphQL API key information type"""
    api_key_id: str
    user_id: str
    permissions: List[str]
    client_ip: Optional[str]

@strawberry.type
class TaskStats:
    """GraphQL task statistics"""
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_processing_time: Optional[float]

@strawberry.type
class TaskSearchResult:
    """GraphQL task search result"""
    tasks: List[TaskType]
    total_count: int

@strawberry.input
class TaskCreateInput:
    """GraphQL task creation input"""
    type: str
    priority: Optional[str] = "medium"
    payload: JSONScalar
    max_retries: Optional[int] = 3
    scheduled_for: Optional[str] = None
    parent_task_id: Optional[str] = None

@strawberry.input
class TaskUpdateInput:
    """GraphQL task update input"""
    priority: Optional[str] = None
    status: Optional[str] = None
    max_retries: Optional[int] = None

def task_to_gql(task: Task) -> TaskType:
    """Convert Task model to GraphQL type"""
    return TaskType(
        id=strawberry.ID(str(task.id)),
        type=task.type.value if hasattr(task.type, 'value') else str(task.type),
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        priority=task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
        payload=task.payload,
        result=task.result,
        error=task.error,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        scheduled_for=task.scheduled_for.isoformat() if hasattr(task.scheduled_for, 'isoformat') else str(task.scheduled_for),
        started_at=task.started_at.isoformat() if hasattr(task.started_at, 'isoformat') else str(task.started_at),
        completed_at=task.completed_at.isoformat() if hasattr(task.completed_at, 'isoformat') else str(task.completed_at),
        created_by=task.created_by,
        parent_task_id=task.parent_task_id,
        created_at=task.created_at.isoformat() if hasattr(task.created_at, 'isoformat') else str(task.created_at),
        updated_at=task.updated_at.isoformat() if hasattr(task.updated_at, 'isoformat') else str(task.updated_at)
    )

@strawberry.type
class TaskQuery:
    """GraphQL queries for tasks"""
    
    @strawberry.field
    @api_key_required("read")
    async def task(self, info, task_id: strawberry.ID) -> TaskType:
        """Get task by ID"""
        api_key_info = info.context["api_key_info"]
        task = await Task.get(str(task_id))
        
        if not task:
            raise Exception("Task not found")
        
        # Check permission - only creator or admin can view
        if (task.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to access this task")
        
        return task_to_gql(task)
    
    @strawberry.field
    @api_key_required("read")
    async def tasks(
        self, 
        info, 
        type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0, 
        limit: int = 10
    ) -> TaskSearchResult:
        """List tasks with optional filtering"""
        api_key_info = info.context["api_key_info"]
        
        task_type = TaskTypeModel(type) if type else None
        task_status = TaskStatus(status) if status else None
        task_priority = TaskPriority(priority) if priority else None
        
        # Non-admin users can only see their own tasks
        if "admin" not in api_key_info.get("permissions", []):
            tasks = await task_service.search_user_tasks(
                api_key_info["casdoor_user_id"], task_type, task_status, task_priority, skip, limit
            )
            total_count = await task_service.get_user_task_count(
                api_key_info["casdoor_user_id"], task_type, task_status, task_priority
            )
        else:
            # Admin users can see all tasks
            tasks = await task_service.search_tasks(task_type, task_status, task_priority, skip, limit)
            total_count = await task_service.get_task_count(task_type, task_status, task_priority)
        
        return TaskSearchResult(
            tasks=[task_to_gql(task) for task in tasks],
            total_count=total_count
        )
    
    @strawberry.field
    @api_key_required("admin")
    async def task_stats(self, info) -> TaskStats:
        """Get task statistics (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        stats = await task_service.get_task_stats()
        return TaskStats(**stats)
    
    @strawberry.field
    @api_key_required("admin")
    async def pending_tasks(
        self, 
        info, 
        task_type: str,
        limit: int = 10
    ) -> List[TaskType]:
        """Get pending tasks of a specific type (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        tasks = await task_service.get_pending_tasks(TaskTypeModel(task_type), limit)
        return [task_to_gql(task) for task in tasks]
    
    @strawberry.field
    @api_key_required("read")
    async def my_tasks(
        self, 
        info, 
        status: Optional[str] = None,
        skip: int = 0, 
        limit: int = 10
    ) -> TaskSearchResult:
        """Get current user's tasks"""
        api_key_info = info.context["api_key_info"]
        
        task_status = TaskStatus(status) if status else None
        
        tasks = await task_service.search_user_tasks(
            api_key_info["casdoor_user_id"], None, task_status, None, skip, limit
        )
        total_count = await task_service.get_user_task_count(
            api_key_info["casdoor_user_id"], None, task_status, None
        )
        
        return TaskSearchResult(
            tasks=[task_to_gql(task) for task in tasks],
            total_count=total_count
        )
    
    @strawberry.field
    @api_key_required("read")
    async def api_key_info(self, info) -> APIKeyInfo:
        """Get current API key information"""
        api_key_info = info.context["api_key_info"]
        return APIKeyInfo(
            api_key_id=api_key_info["api_key_id"],
            user_id=api_key_info["casdoor_user_id"],
            permissions=api_key_info.get("permissions", []),
            client_ip=api_key_info.get("client_ip")
        )

@strawberry.type
class TaskMutation:
    """GraphQL mutations for tasks"""
    
    @strawberry.mutation
    @api_key_required("write")
    async def create_task(
        self, 
        info, 
        task_data: TaskCreateInput
    ) -> TaskType:
        """Create a new task"""
        api_key_info = info.context["api_key_info"]
        
        # Convert to Pydantic model
        task_dict = {k: v for k, v in task_data.__dict__.items() if v is not None}
        task_model = TaskCreate(**task_dict)
        
        task = await task_service.create_task(task_model, api_key_info["casdoor_user_id"])
        return task_to_gql(task)
    
    @strawberry.mutation
    @api_key_required("write")
    async def update_task(
        self, 
        info, 
        task_id: strawberry.ID,
        update_data: TaskUpdateInput
    ) -> TaskType:
        """Update task"""
        api_key_info = info.context["api_key_info"]
        
        # First check if task exists
        existing_task = await Task.get(str(task_id))
        if not existing_task:
            raise Exception("Task not found")
        
        # Check permission - only creator or admin can update
        if (existing_task.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to update this task")
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = TaskUpdate(**update_dict)
        
        # Convert to dict for update
        update_data_dict = update_model.model_dump(exclude_unset=True)
        task = await task_service.update_task(str(task_id), update_data_dict)
        
        if not task:
            raise Exception("Task not found")
        
        return task_to_gql(task)
    
    @strawberry.mutation
    @api_key_required("write")
    async def delete_task(
        self, 
        info, 
        task_id: strawberry.ID
    ) -> bool:
        """Delete task"""
        api_key_info = info.context["api_key_info"]
        
        # First check if task exists
        existing_task = await Task.get(str(task_id))
        if not existing_task:
            raise Exception("Task not found")
        
        # Check permission - only creator or admin can delete
        if (existing_task.created_by != api_key_info["casdoor_user_id"] and 
            "admin" not in api_key_info.get("permissions", [])):
            raise Exception("Not authorized to delete this task")
        
        success = await task_service.delete_task(str(task_id))
        
        if not success:
            raise Exception("Task not found")
        
        return True
    
    @strawberry.mutation
    @api_key_required("admin")
    async def retry_task(
        self, 
        info, 
        task_id: strawberry.ID
    ) -> bool:
        """Retry a failed task (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        success = await task_service.retry_task(str(task_id))
        
        if not success:
            raise Exception("Task not found or cannot be retried")
        
        return True
    
    @strawberry.mutation
    @api_key_required("admin")
    async def cancel_task(
        self, 
        info, 
        task_id: strawberry.ID
    ) -> bool:
        """Cancel a task (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        success = await task_service.cancel_task(str(task_id))
        
        if not success:
            raise Exception("Task not found or cannot be cancelled")
        
        return True
    
    @strawberry.mutation
    @api_key_required("admin")
    async def bulk_update_tasks(
        self, 
        info, 
        task_ids: List[strawberry.ID],
        update_data: TaskUpdateInput
    ) -> List[TaskType]:
        """Bulk update multiple tasks (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        # Convert to Pydantic model
        update_dict = {k: v for k, v in update_data.__dict__.items() if v is not None}
        update_model = TaskUpdate(**update_dict)
        
        # Convert to dict for update
        update_data_dict = update_model.model_dump(exclude_unset=True)
        
        updated_tasks = []
        for task_id in task_ids:
            task = await task_service.update_task(str(task_id), update_data_dict)
            if task:
                updated_tasks.append(task_to_gql(task))
        
        return updated_tasks
    
    @strawberry.mutation
    @api_key_required("admin")
    async def cleanup_tasks(
        self, 
        info, 
        older_than_days: int = 30,
        status: Optional[str] = "completed"
    ) -> int:
        """Clean up old tasks (admin only)"""
        api_key_info = info.context["api_key_info"]
        # Admin check is handled by require_admin dependency
        
        task_status = TaskStatus(status) if status else None
        deleted_count = await task_service.cleanup_tasks(older_than_days, task_status)
        
        return deleted_count

# Schema definition
task_schema = strawberry.Schema(
    query=TaskQuery,
    mutation=TaskMutation,
    types=[TaskType, TaskStats, TaskSearchResult, APIKeyInfo]
)