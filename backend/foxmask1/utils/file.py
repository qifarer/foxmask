
import uuid
import time
from typing import Optional, Dict

def generate_uuid() -> str:
    return str(uuid.uuid4())

def generate_file_path_metadata(
    original_filename: str,
    directory: Optional[str] = None,
    pathname: Optional[str] = None
) -> Dict[str, str]:
    """生成文件存储路径元数据"""
    extension = original_filename.split('.')[-1] if '.' in original_filename else ''
    filename = f"{generate_uuid()}.{extension}" if extension else generate_uuid()
    
    # 生成基于时间戳的目录路径
    date = str(int(time.time() / 3600))  # 每小时一个目录
    dirname = directory or "uploads"
    full_dirname = f"{dirname}/{date}"
    pathname = pathname or f"{full_dirname}/{filename}"
    
    return {
        "date": date,
        "dirname": full_dirname,
        "filename": filename,
        "pathname": pathname
    }

def parse_data_uri(data_uri: str) -> Dict[str, str]:
    """解析数据URI"""
    if not data_uri.startswith('data:'):
        return {"type": "invalid", "base64": None, "mime_type": None}
    
    parts = data_uri.split(',', 1)
    if len(parts) != 2:
        return {"type": "invalid", "base64": None, "mime_type": None}
    
    header = parts[0]
    data = parts[1]
    
    mime_type = header.split(';')[0].replace('data:', '')
    
    if 'base64' in header:
        return {"type": "base64", "base64": data, "mime_type": mime_type}
    else:
        return {"type": "plain", "base64": None, "mime_type": mime_type, "data": data}