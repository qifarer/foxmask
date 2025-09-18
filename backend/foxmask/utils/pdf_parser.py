import fitz  # PyMuPDF
import re
from typing import Optional, Tuple, Dict, List
import html
from dataclasses import dataclass
import pandas as pd
import cv2
import numpy as np
from PIL import Image
import io

@dataclass
class PDFMetadata:
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    mod_date: Optional[str] = None

class PDFParser:
    def __init__(self):
        self.heading_patterns = [
            (r'^第[一二三四五六七八九十]+章\s+.+$', 1),
            (r'^第\d+章\s+.+$', 1),
            (r'^\d+\.\d+\s+.+$', 2),
            (r'^\d+\.\s+.+$', 2),
            (r'^[A-Z][A-Z\s]+$', 1),  # 全大写的英文标题
            (r'^[一二三四五六七八九十]、.+$', 2),
            (r'^\(\d+\)\s+.+$', 3),
        ]

    def extract_metadata(self, doc: fitz.Document) -> PDFMetadata:
        """提取PDF元数据"""
        metadata = doc.metadata
        return PDFMetadata(
            title=metadata.get('title'),
            author=metadata.get('author'),
            subject=metadata.get('subject'),
            keywords=metadata.get('keywords'),
            creator=metadata.get('creator'),
            producer=metadata.get('producer'),
            creation_date=metadata.get('creationDate'),
            mod_date=metadata.get('modDate')
        )

    def detect_heading_level(self, text: str) -> Optional[int]:
        """检测文本的标题级别"""
        text = text.strip()
        for pattern, level in self.heading_patterns:
            if re.match(pattern, text):
                return level
        return None

    def extract_text_with_structure(self, doc: fitz.Document) -> List[Dict]:
        """提取带结构的文本"""
        structured_content = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                            
                            # 检测字体特征判断标题
                            font_size = span["size"]
                            font_flags = span["flags"]
                            
                            # 判断是否为标题的启发式规则
                            is_bold = font_flags & 2 ** 4  # 粗体
                            is_italic = font_flags & 2 ** 1  # 斜体
                            
                            heading_level = self.detect_heading_level(text)
                            if not heading_level and is_bold and font_size > 12:
                                heading_level = 2
                            
                            structured_content.append({
                                "text": text,
                                "page": page_num + 1,
                                "font_size": font_size,
                                "is_bold": bool(is_bold),
                                "is_italic": bool(is_italic),
                                "heading_level": heading_level
                            })
        
        return structured_content

    def parse_pdf_to_markdown(self, file_path: str) -> Tuple[Optional[str], Optional[PDFMetadata]]:
        """解析PDF文件为Markdown格式"""
        try:
            doc = fitz.open(file_path)
            metadata = self.extract_metadata(doc)
            structured_content = self.extract_text_with_structure(doc)
            
            md_lines = []
            
            # 添加文档标题
            if metadata.title:
                md_lines.append(f"# {metadata.title}\n")
            else:
                md_lines.append("# Document\n")
            
            # 添加元数据
            if any([metadata.author, metadata.creation_date]):
                md_lines.append("## Metadata\n")
                if metadata.author:
                    md_lines.append(f"- **Author**: {metadata.author}")
                if metadata.creation_date:
                    md_lines.append(f"- **Creation Date**: {metadata.creation_date}")
                md_lines.append("")
            
            # 处理内容
            current_heading_level = 0
            
            for item in structured_content:
                text = item["text"]
                
                if item["heading_level"]:
                    # 处理标题
                    level = item["heading_level"]
                    hashes = "#" * level
                    md_lines.append(f"{hashes} {text}\n")
                    current_heading_level = level
                
                elif item["is_bold"] and item["font_size"] > 11:
                    # 可能是小标题或强调文本
                    md_lines.append(f"**{text}**")
                
                elif text.startswith(('•', '▪', '‣', '⁃')) or text.startswith(('●', '○', '◆', '■')):
                    # 列表项
                    md_lines.append(f"- {text[1:].strip()}")
                
                elif re.match(r'^\d+[\.\)]', text):
                    # 编号列表
                    md_lines.append(f"1. {text}")
                
                else:
                    # 普通段落
                    if md_lines and not md_lines[-1].endswith(('\n', '-', '**')):
                        md_lines[-1] += " " + text
                    else:
                        md_lines.append(text)
            
            doc.close()
            
            # 清理和格式化Markdown
            md_content = self._clean_markdown("\n".join(md_lines))
            return md_content, metadata
            
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return None, None

    def _clean_markdown(self, md_text: str) -> str:
        """清理和格式化Markdown文本"""
        # 移除多余的空行
        md_text = re.sub(r'\n\s*\n', '\n\n', md_text)
        
        # 确保段落之间有适当的间距
        md_text = re.sub(r'([^\n])\n([^\n#\-])', r'\1 \2', md_text)
        
        # 清理特殊字符
        md_text = html.unescape(md_text)
        md_text = re.sub(r'[^\x00-\x7F]+', ' ', md_text)  # 移除非ASCII字符
        
        return md_text.strip()

    def extract_tables(self, file_path: str) -> List[str]:
        """提取PDF中的表格（基础版本）"""
        try:
            doc = fitz.open(file_path)
            tables = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                # 简单的表格检测（基于对齐的文本）
                lines = text.split('\n')
                table_lines = []
                in_table = False
                
                for line in lines:
                    # 检测可能是表格行的模式
                    if re.match(r'^(\s*\S+\s+){2,}\S+\s*$', line):
                        if not in_table:
                            table_lines.append("| " + " | ".join(line.split()) + " |")
                            table_lines.append("|" + " --- |" * (len(line.split()) + 1))
                            in_table = True
                        else:
                            table_lines.append("| " + " | ".join(line.split()) + " |")
                    else:
                        if in_table and table_lines:
                            tables.append("\n".join(table_lines))
                            table_lines = []
                        in_table = False
                
                if table_lines:
                    tables.append("\n".join(table_lines))
            
            doc.close()
            return tables
            
        except Exception as e:
            print(f"Error extracting tables: {e}")
            return []

    def parse_pdf_to_text(self, file_path: str) -> Optional[str]:
        """提取PDF纯文本内容"""
        try:
            doc = fitz.open(file_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text() + "\n\n"
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None

    def extract_images(self, file_path: str, output_dir: str) -> List[str]:
        """提取PDF中的图像"""
        try:
            doc = fitz.open(file_path)
            image_paths = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 保存图像
                    image_ext = base_image["ext"]
                    image_filename = f"page_{page_num+1}_img_{img_index+1}.{image_ext}"
                    image_path = f"{output_dir}/{image_filename}"
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    image_paths.append(image_path)
            
            doc.close()
            return image_paths
            
        except Exception as e:
            print(f"Error extracting images: {e}")
            return []

    def extract_links(self, file_path: str) -> List[Dict]:
        """提取PDF中的链接"""
        try:
            doc = fitz.open(file_path)
            links = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                link_dict = page.get_links()
                
                for link in link_dict:
                    if 'uri' in link:
                        links.append({
                            'page': page_num + 1,
                            'url': link['uri'],
                            'rect': link.get('rect', [])
                        })
            
            doc.close()
            return links
            
        except Exception as e:
            print(f"Error extracting links: {e}")
            return []

    def extract_with_coordinates(self, file_path: str) -> List[Dict]:
        """基于坐标提取文本，保留布局信息"""
        try:
            doc = fitz.open(file_path)
            content_with_coords = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_instances = page.get_text("rawdict")
                
                for block in text_instances["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                content_with_coords.append({
                                    'text': span["text"],
                                    'page': page_num + 1,
                                    'bbox': span["bbox"],
                                    'font': span["font"],
                                    'size': span["size"],
                                    'color': span["color"]
                                })
            
            doc.close()
            return content_with_coords
            
        except Exception as e:
            print(f"Error extracting text with coordinates: {e}")
            return []
        
pdf_parser = PDFParser()      

# 使用示例
if __name__ == "__main__":
    parser = PDFParser()
    
    # 示例用法
    md_content, metadata = parser.parse_pdf_to_markdown("example.pdf")
    if md_content:
        print("Markdown content:")
        print(md_content[:500] + "..." if len(md_content) > 500 else md_content)
        
        print("\nMetadata:")
        print(f"Title: {metadata.title}")
        print(f"Author: {metadata.author}")
    
    # 提取纯文本
    text_content = parser.parse_pdf_to_text("example.pdf")
    if text_content:
        print(f"\nText content (first 200 chars):")
        print(text_content[:200] + "...")