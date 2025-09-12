import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import asyncio

from .logger import logger

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint', 'status']
)

DATABASE_OPERATIONS = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'collection', 'success']
)

DATABASE_LATENCY = Histogram(
    'database_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'collection']
)

EXTERNAL_SERVICE_CALLS = Counter(
    'external_service_calls_total',
    'Total external service calls',
    ['service', 'operation', 'success']
)

EXTERNAL_SERVICE_LATENCY = Histogram(
    'external_service_latency_seconds',
    'External service call latency in seconds',
    ['service', 'operation']
)

class MonitoringService:
    """Monitoring and metrics service"""
    
    @staticmethod
    async def track_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Track HTTP request metrics"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        if request_size is not None:
            REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(request_size)
        
        if response_size is not None:
            RESPONSE_SIZE.labels(method=method, endpoint=endpoint, status=status_code).observe(response_size)
    
    @staticmethod
    async def track_database_operation(
        operation: str,
        collection: str,
        duration: float,
        success: bool = True
    ):
        """Track database operation metrics"""
        DATABASE_OPERATIONS.labels(
            operation=operation,
            collection=collection,
            success=str(success)
        ).inc()
        
        DATABASE_LATENCY.labels(
            operation=operation,
            collection=collection
        ).observe(duration)
    
    @staticmethod
    async def track_external_service_call(
        service: str,
        operation: str,
        duration: float,
        success: bool = True
    ):
        """Track external service call metrics"""
        EXTERNAL_SERVICE_CALLS.labels(
            service=service,
            operation=operation,
            success=str(success)
        ).inc()
        
        EXTERNAL_SERVICE_LATENCY.labels(
            service=service,
            operation=operation
        ).observe(duration)
    
    @staticmethod
    async def metrics_endpoint():
        """Generate Prometheus metrics"""
        return Response(
            content=generate_latest(),
            media_type="text/plain"
        )
    
    @staticmethod
    def time_operation(operation_name: str) -> Callable:
        """Decorator to time operations"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.performance(operation_name, duration * 1000)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.performance(operation_name, duration * 1000)
                    raise
            
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.performance(operation_name, duration * 1000)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.performance(operation_name, duration * 1000)
                    raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator

# Global monitoring service instance
monitoring_service = MonitoringService()