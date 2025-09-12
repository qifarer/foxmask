import os
import tempfile
import requests
from typing import List, Dict, Any
from knowledge.models import KnowledgeType

class FileParser:
    async def parse_files(self, file_paths: List[str], knowledge_type: KnowledgeType) -> Dict[str, Any]:
        parsed_content = {
            "title": "",
            "description": "",
            "content": "",
            "entities": []
        }
        
        for file_path in file_paths:
            if file_path.startswith(('http://', 'https://')):
                # 下载远程文件
                content = await self._download_file(file_path)
            else:
                # 读取本地文件
                content = await self._read_local_file(file_path)
            
            # 根据知识类型解析内容
            if knowledge_type == KnowledgeType.DOCUMENT:
                parsed_content["content"] += await self._parse_document(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.IMAGE:
                parsed_content["content"] += await self._parse_image(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.VIDEO:
                parsed_content["content"] += await self._parse_video(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.AUDIO:
                parsed_content["content"] += await self._parse_audio(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.CODE:
                parsed_content["content"] += await self._parse_code(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.PRESENTATION:
                parsed_content["content"] += await self._parse_presentation(content, file_path) + "\n\n"
            elif knowledge_type == KnowledgeType.SPREADSHEET:
                parsed_content["content"] += await self._parse_spreadsheet(content, file_path) + "\n\n"
            else:
                parsed_content["content"] += f"[Unsupported knowledge type: {knowledge_type}]\n\n"
        
        # 提取标题和描述
        if parsed_content["content"]:
            lines = parsed_content["content"].split('\n')
            parsed_content["title"] = lines[0] if lines else "Untitled"
            parsed_content["description"] = lines[1] if len(lines) > 1 else ""
        
        return parsed_content
    
    async def _download_file(self, url: str) -> str:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error downloading file: {e}")
            return f"Error downloading file from {url}"
    
    async def _read_local_file(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return f"Error reading file {file_path}"
    
    async def _parse_document(self, content: str, file_path: str) -> str:
        # 根据文件扩展名处理文档
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.txt', '.md']:
            return content
        elif file_ext in ['.pdf']:
            return await self._parse_pdf(content)
        elif file_ext in ['.doc', '.docx']:
            return await self._parse_doc(content)
        else:
            return f"[Unsupported document format: {file_ext}]\n\n{content}"
    
    async def _parse_image(self, content: str, file_path: str) -> str:
        # 图像处理逻辑
        return f"Image content from {file_path}"
    
    async def _parse_video(self, content: str, file_path: str) -> str:
        # 视频处理逻辑
        return f"Video content from {file_path}"
    
    async def _parse_audio(self, content: str, file_path: str) -> str:
        # 音频处理逻辑
        return f"Audio content from {file_path}"
    
    async def _parse_code(self, content: str, file_path: str) -> str:
        # 代码处理逻辑
        return f"Code content from {file_path}"
    
    async def _parse_presentation(self, content: str, file_path: str) -> str:
        # 演示文稿处理逻辑
        return f"Presentation content from {file_path}"
    
    async def _parse_spreadsheet(self, content: str, file_path: str) -> str:
        # 电子表格处理逻辑
        return f"Spreadsheet content from {file_path}"
    
    async def _parse_pdf(self, content: str) -> str:
        # 简单的PDF文本提取
        # 实际应用中应使用专门的PDF解析库如PyPDF2
        return content
    
    async def _parse_doc(self, content: str) -> str:
        # 简单的DOC文本提取
        # 实际应用中应使用专门的DOC解析库如python-docx
        return content