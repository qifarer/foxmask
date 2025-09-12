import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from task.services import TaskService
from task.models import Task, TaskStatus, TaskType, TaskPriority

class TestTaskService:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, test_db):
        self.task_service = TaskService()
        self.test_db = test_db

    @pytest.mark.asyncio
    async def test_create_task(self):
        """Test creating a task."""
        from task.schemas import TaskCreate
        task_data = TaskCreate(
            type=TaskType.KNOWLEDGE_PROCESSING,
            priority=TaskPriority.HIGH,
            payload={"item_id": "test-item-123"},
            max_retries=3
        )
        
        task = await self.task_service.create_task(task_data, "test-user-123")
        
        assert task is not None
        assert task.type == TaskType.KNOWLEDGE_PROCESSING
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.created_by == "test-user-123"

    @pytest.mark.asyncio
    async def test_process_task_success(self):
        """Test successful task processing."""
        # Create a test task
        task = Task(
            type=TaskType.KNOWLEDGE_PROCESSING,
            payload={"item_id": "test-item-123"}
        )
        await task.insert()
        
        # Mock processor function
        mock_processor = AsyncMock(return_value={"result": "success"})
        
        result = await self.task_service.process_task(str(task.id), mock_processor)
        
        assert result is True
        
        # Verify task was updated
        updated_task = await self.task_service.get_task(str(task.id))
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.result == {"result": "success"}
        assert updated_task.started_at is not None
        assert updated_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_process_task_failure(self):
        """Test failed task processing."""
        # Create a test task
        task = Task(
            type=TaskType.KNOWLEDGE_PROCESSING,
            payload={"item_id": "test-item-123"}
        )
        await task.insert()
        
        # Mock processor function that raises an exception
        mock_processor = AsyncMock(side_effect=Exception("Processing failed"))
        
        result = await self.task_service.process_task(str(task.id), mock_processor)
        
        assert result is False
        
        # Verify task was marked as failed
        updated_task = await self.task_service.get_task(str(task.id))
        assert updated_task.status == TaskStatus.FAILED
        assert updated_task.error == "Processing failed"

    @pytest.mark.asyncio
    async def test_retry_task(self):
        """Test retrying a failed task."""
        # Create a failed task
        task = Task(
            type=TaskType.KNOWLEDGE_PROCESSING,
            status=TaskStatus.FAILED,
            retry_count=0,
            max_retries=3,
            payload={"item_id": "test-item-123"}
        )
        await task.insert()
        
        # Mock Kafka
        with patch('task.services.kafka_manager') as mock_kafka:
            mock_kafka.send_message = AsyncMock()
            
            result = await self.task_service.retry_task(str(task.id))
            
            assert result is True
            
            # Verify task was reset
            updated_task = await self.task_service.get_task(str(task.id))
            assert updated_task.status == TaskStatus.PENDING
            assert updated_task.retry_count == 1
            
            # Verify Kafka message was sent
            mock_kafka.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_tasks(self):
        """Test getting pending tasks."""
        # Create tasks with different statuses
        pending_task = Task(
            type=TaskType.KNOWLEDGE_PROCESSING,
            status=TaskStatus.PENDING
        )
        await pending_task.insert()
        
        completed_task = Task(
            type=TaskType.KNOWLEDGE_PROCESSING,
            status=TaskStatus.COMPLETED
        )
        await completed_task.insert()
        
        pending_tasks = await self.task_service.get_pending_tasks(
            TaskType.KNOWLEDGE_PROCESSING
        )
        
        assert len(pending_tasks) == 1
        assert pending_tasks[0].status == TaskStatus.PENDING