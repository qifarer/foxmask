import logging
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone 
from enum import Enum, IntEnum
from contextvars import ContextVar
import uuid

from .config import settings

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# 使用 IntEnum 来匹配 Python logging 的整数级别
class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "correlation_id": correlation_id_var.get(),
            "thread": record.threadName,
            "process": record.processName,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": self.formatException(record.exc_info)
            }
        
        # Add extra data from log record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)

class StructuredLogger:
    """Structured logger with context support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.request_id = request_id_var.get
        self.user_id = user_id_var.get
        self.correlation_id = correlation_id_var.get
    
    def _log_with_context(
        self,
        level: int,  # 改为使用整数级别
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """Log with context information"""
        log_extra = extra or {}
        log_extra.update({
            "request_id": self.request_id(),
            "user_id": self.user_id(),
            "correlation_id": self.correlation_id(),
        })
        
        if exc_info:
            self.logger.log(
                level,  # 直接使用整数级别
                message,
                extra=log_extra,
                exc_info=exc_info
            )
        else:
            self.logger.log(level, message, extra=log_extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_context(logging.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_context(logging.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        self._log_with_context(logging.WARNING, message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None):
        self._log_with_context(logging.ERROR, message, extra, exc_info)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: Optional[Exception] = None):
        self._log_with_context(logging.CRITICAL, message, extra, exc_info)
    
    def audit(self, action: str, resource_type: str, resource_id: str, extra: Optional[Dict[str, Any]] = None):
        """Audit logging for security events"""
        audit_extra = extra or {}
        audit_extra.update({
            "audit_action": action,
            "audit_resource_type": resource_type,
            "audit_resource_id": resource_id,
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_user_id": self.user_id(),
        })
        self.info(f"Audit: {action} on {resource_type} {resource_id}", audit_extra)
    
    def performance(self, operation: str, duration_ms: float, extra: Optional[Dict[str, Any]] = None):
        """Performance logging"""
        perf_extra = extra or {}
        perf_extra.update({
            "perf_operation": operation,
            "perf_duration_ms": duration_ms,
            "perf_timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.info(f"Performance: {operation} took {duration_ms}ms", perf_extra)

def setup_logger():
    """Setup application logger with structured logging"""
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Set JSON formatter
    formatter = JSONFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Add file handler for production
    if not settings.DEBUG:
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                f"/var/log/{settings.APP_NAME}/app.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # 使用基本的 logging 来记录错误，避免循环依赖
            basic_logger = logging.getLogger(__name__)
            basic_logger.warning(f"Failed to setup file logging: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)

# 初始化日志系统
setup_logger()

# Global logger instance
logger = get_logger(settings.APP_NAME)

# Request context management
class RequestContext:
    """Manage request context for logging"""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id or ""
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self._request_token = None
        self._user_token = None
        self._correlation_token = None
    
    def __enter__(self):
        self._request_token = request_id_var.set(self.request_id)
        self._user_token = user_id_var.set(self.user_id)
        self._correlation_token = correlation_id_var.set(self.correlation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._request_token:
            request_id_var.reset(self._request_token)
        if self._user_token:
            user_id_var.reset(self._user_token)
        if self._correlation_token:
            correlation_id_var.reset(self._correlation_token)

def log_exception(logger: StructuredLogger, exception: Exception, context: Optional[Dict[str, Any]] = None):
    """Log exception with full context"""
    extra = context or {}
    extra.update({
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "exception_module": exception.__class__.__module__,
    })
    
    logger.error(
        f"Exception occurred: {type(exception).__name__}: {str(exception)}",
        extra=extra,
        exc_info=exception
    )