# -*- coding: utf-8 -*-
# General helper utilities

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
from bson import ObjectId


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())

def generate_short_id() -> str:
    """Generate a short unique ID"""
    return uuid.uuid4().hex[:8]

def get_current_time() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def format_timestamp(timestamp: datetime) -> str:
    """Format datetime to ISO string"""
    return timestamp.isoformat()

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO string to datetime"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

def is_valid_object_id(object_id: str) -> bool:
    """Check if a string is a valid MongoDB ObjectId"""
    try:
        ObjectId(object_id)
        return True
    except Exception:
        return False

def convert_objectids_to_strings(data: Any) -> Any:
    """
    递归地将所有 ObjectId 转换为字符串
    """
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_objectids_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectids_to_strings(item) for item in data]
    else:
        return data

def calculate_md5_hash(data: bytes) -> str:
    """Calculate MD5 hash of data"""
    return hashlib.md5(data).hexdigest()

def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if (key in result and isinstance(result[key], dict) 
            and isinstance(value, dict)):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def safe_json_loads(json_str: str) -> Optional[Dict]:
    """Safely parse JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove unsafe characters"""
    # Remove directory traversal attempts
    filename = filename.replace("../", "").replace("./", "")
    # Remove unsafe characters
    filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    return filename

def generate_presigned_url_expiry(minutes: int = 60) -> int:
    """Generate expiry time for presigned URLs"""
    return int((get_current_time().timestamp() + minutes * 60))