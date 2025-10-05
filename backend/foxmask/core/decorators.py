# foxmask/utils/decorators.py
import functools
from typing import Any, Callable, Type, Union
from loguru import logger
from foxmask.core.exceptions import (
    KnowledgeBaseException, DatabaseException, ServiceException, 
    ValidationException, NotFoundException
)


def handle_exceptions(
    exception_mapping: dict = None,
    default_message: str = "An unexpected error occurred",
    log_level: str = "ERROR"
):
    """
    异常处理装饰器
    
    Args:
        exception_mapping: 异常类型到错误消息的映射
        default_message: 默认错误消息
        log_level: 日志级别
    """
    if exception_mapping is None:
        exception_mapping = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                logger.debug(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
                result = await func(*args, **kwargs)
                logger.debug(f"Successfully executed {func.__name__}")
                return result
            except KnowledgeBaseException:
                # 已知异常，直接抛出
                raise
            except Exception as e:
                # 未知异常，根据映射处理或使用默认消息
                error_message = exception_mapping.get(type(e), default_message)
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                
                # 根据异常类型创建相应的自定义异常
                if isinstance(e, ValueError):
                    raise ValidationException(error_message) from e
                elif isinstance(e, KeyError):
                    raise ValidationException(f"Missing required field: {str(e)}") from e
                else:
                    raise ServiceException(
                        func.__module__, 
                        func.__name__, 
                        f"{error_message}: {str(e)}"
                    ) from e
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                logger.debug(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
                result = func(*args, **kwargs)
                logger.debug(f"Successfully executed {func.__name__}")
                return result
            except KnowledgeBaseException:
                raise
            except Exception as e:
                error_message = exception_mapping.get(type(e), default_message)
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                
                if isinstance(e, ValueError):
                    raise ValidationException(error_message) from e
                elif isinstance(e, KeyError):
                    raise ValidationException(f"Missing required field: {str(e)}") from e
                else:
                    raise ServiceException(
                        func.__module__, 
                        func.__name__, 
                        f"{error_message}: {str(e)}"
                    ) from e
        
        # 根据函数类型返回相应的包装器
        if func.__code__.co_flags & 0x80:  # 检查是否是异步函数
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """记录函数执行时间的装饰器"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        import time
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
    
    if func.__code__.co_flags & 0x80:
        return async_wrapper
    else:
        return sync_wrapper


def validate_arguments(required_fields: list = None) -> Callable:
    """参数验证装饰器"""
    if required_fields is None:
        required_fields = []
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # 检查必需字段
            for field in required_fields:
                if field not in kwargs or kwargs[field] is None:
                    raise ValidationException(f"Missing required field: {field}", field)
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            for field in required_fields:
                if field not in kwargs or kwargs[field] is None:
                    raise ValidationException(f"Missing required field: {field}", field)
            
            return func(*args, **kwargs)
        
        if func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator