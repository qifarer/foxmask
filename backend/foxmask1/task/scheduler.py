from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from core.config import settings

class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        # 添加定时任务
        # 例如：每5分钟检查一次处理失败的知识条目
        self.scheduler.add_job(
            self.retry_failed_items,
            IntervalTrigger(minutes=5),
            id="retry_failed_items",
            name="Retry processing failed knowledge items",
            replace_existing=True
        )
        
        self.scheduler.start()
    
    async def retry_failed_items(self):
        from knowledge.service import knowledge_item_service
        from knowledge.model import ItemStatus
        from task.producer import send_knowledge_item_created
        
        # 获取所有处理失败的知识条目
        failed_items = await knowledge_item_service.list_failed_items()
        
        for item in failed_items:
            # 重新发送处理消息
            await send_knowledge_item_created(
                str(item.id),
                item.source_type.value,
                item.knowledge_type.value,
                item.sources
            )
            
            # 更新状态为重新处理中
            await knowledge_item_service.update_item_status(item.id, ItemStatus.CREATED)

# 全局调度器实例
task_scheduler = TaskScheduler()