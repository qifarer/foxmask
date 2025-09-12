from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from .logger import logger

class AuditAction(str, Enum):
    """Audit action types"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    DOWNLOAD = "DOWNLOAD"
    UPLOAD = "UPLOAD"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"

class AuditResourceType(str, Enum):
    """Audit resource types"""
    USER = "USER"
    FILE = "FILE"
    KNOWLEDGE_ITEM = "KNOWLEDGE_ITEM"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    TAG = "TAG"
    TASK = "TASK"
    API_KEY = "API_KEY"

class AuditService:
    """Audit logging service"""
    
    @staticmethod
    def log(
        action: AuditAction,
        resource_type: AuditResourceType,
        resource_id: str,
        user_id: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log an audit event"""
        audit_data = {
            "audit_action": action.value,
            "audit_resource_type": resource_type.value,
            "audit_resource_id": resource_id,
            "audit_user_id": user_id,
            "audit_success": success,
            "audit_timestamp": datetime.utcnow().isoformat(),
            "audit_details": details or {},
        }
        
        if ip_address:
            audit_data["audit_ip_address"] = ip_address
        if user_agent:
            audit_data["audit_user_agent"] = user_agent
        
        # Log at INFO level for success, WARNING for failures
        if success:
            logger.info(
                f"Audit: {action.value} {resource_type.value} {resource_id}",
                audit_data
            )
        else:
            logger.warning(
                f"Audit failed: {action.value} {resource_type.value} {resource_id}",
                audit_data
            )
    
    @staticmethod
    def log_security_event(
        event_type: str,
        severity: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log a security-related event"""
        security_data = {
            "security_event_type": event_type,
            "security_severity": severity,
            "security_timestamp": datetime.utcnow().isoformat(),
            "security_details": details or {},
        }
        
        if user_id:
            security_data["security_user_id"] = user_id
        if ip_address:
            security_data["security_ip_address"] = ip_address
        
        # Log based on severity
        if severity == "HIGH":
            logger.critical(f"Security alert: {event_type}", security_data)
        elif severity == "MEDIUM":
            logger.error(f"Security event: {event_type}", security_data)
        else:
            logger.warning(f"Security notice: {event_type}", security_data)

# Global audit service instance
audit_service = AuditService()