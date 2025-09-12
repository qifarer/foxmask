import base64
from io import BytesIO
from PIL import Image
from typing import Optional, Dict
from fastapi import UploadFile

async def get_image_dimensions(file_or_base64) -> Optional[Dict[str, int]]:
    """获取图片尺寸（支持大文件流式处理）"""
    try:
        if isinstance(file_or_base64, str) and file_or_base64.startswith('data:image'):
            # 处理 base64
            header, data = file_or_base64.split(',', 1)
            image_data = base64.b64decode(data)
            img = Image.open(BytesIO(image_data))
            return {"width": img.width, "height": img.height}
        else:
            # 处理文件对象 - 只读取前几KB来判断尺寸
            current_pos = await file_or_base64.tell()
            chunk = await file_or_base64.read(1024 * 10)  # 读取10KB
            await file_or_base64.seek(current_pos)  # 回到原来的位置
            
            img = Image.open(BytesIO(chunk))
            return {"width": img.width, "height": img.height}
            
    except Exception:
        return None