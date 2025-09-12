import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import os
import tempfile


class WebCrawler:
    async def crawl_pages(self, urls: List[str]) -> Dict[str, Any]:
        parsed_content = {
            "title": "",
            "description": "",
            "content": "",
            "entities": []
        }
        
        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取标题
                title = soup.find('title')
                if title:
                    parsed_content["title"] = title.get_text()
                
                # 提取描述
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    parsed_content["description"] = meta_desc.get('content')
                
                # 提取主要内容
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content_text = main_content.get_text(separator='\n', strip=True)
                else:
                    # 如果没有明确的主内容区域，提取所有段落
                    paragraphs = soup.find_all('p')
                    content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])
                
                parsed_content["content"] += f"# {parsed_content.get('title', '')}\n\n{content_text}\n\n"
                
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                parsed_content["content"] += f"Error crawling {url}: {str(e)}\n\n"
        
        return parsed_content
    

class FileParser:
    async def parse_files(self, file_paths: List[str]) -> Dict[str, Any]:
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
            
            # 根据文件类型解析内容
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.txt', '.md']:
                parsed_content["content"] += content + "\n\n"
            elif file_ext in ['.pdf']:
                parsed_content["content"] += await self._parse_pdf(content) + "\n\n"
            elif file_ext in ['.doc', '.docx']:
                parsed_content["content"] += await self._parse_doc(content) + "\n\n"
            else:
                parsed_content["content"] += f"[Unsupported file type: {file_ext}]\n\n"
        
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
    
    async def _parse_pdf(self, content: str) -> str:
        # 简单的PDF文本提取
        # 实际应用中应使用专门的PDF解析库如PyPDF2
        return content
    
    async def _parse_doc(self, content: str) -> str:
        # 简单的DOC文本提取
        # 实际应用中应使用专门的DOC解析库如python-docx
        return content    