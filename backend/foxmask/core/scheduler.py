from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from .logger import logger

class Scheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}

    def add_job(self, func, trigger_type, **trigger_args):
        """Add a job to the scheduler"""
        if trigger_type == 'cron':
            trigger = CronTrigger(**trigger_args)
        elif trigger_type == 'interval':
            trigger = IntervalTrigger(**trigger_args)
        else:
            raise ValueError(f"Unsupported trigger type: {trigger_type}")
        
        job = self.scheduler.add_job(func, trigger)
        self.jobs[job.id] = job
        logger.info(f"Added job {func.__name__} with trigger {trigger_type}")
        return job

    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")

scheduler = Scheduler()