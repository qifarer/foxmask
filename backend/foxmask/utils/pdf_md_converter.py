import os
import fitz  # PyMuPDF
import cv2
import numpy as np
import pandas as pd
import json
import time
import uuid
from datetime import datetime
from PIL import Image
from paddleocr import PaddleOCR
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import argparse
import yaml

from foxmask.core.logger import logger


# 配置管理
class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "general": {
            "max_workers": 4,
            "timeout": 3600,
            "temp_dir": "./temp_pdf_content",
            "log_level": "INFO",
            "log_file": None,
        },
        "ocr": {
            "use_gpu": False,
            "lang": "ch",
            "use_angle_cls": True,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "show_log": False,
        },
        "processing": {
            "dpi": 300,
            "min_table_area": 5000,
            "min_formula_area": 100,
            "row_threshold": 20,
            "max_pages": None,  # None表示处理所有页面
            "skip_pages": [],   # 要跳过的页码列表
        },
        "output": {
            "include_images": True,
            "include_tables": True,
            "include_formulas": True,
            "include_text": True,
            "page_headers": True,
            "table_images": True,  # 是否在表格旁边包含表格图像
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """从YAML文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                self._deep_update(self.config, loaded_config)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}, 使用默认配置")
    
    def _deep_update(self, original: Dict, update: Dict) -> None:
        """深度更新字典"""
        for key, value in update.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            return self.config[section][key]
        except KeyError:
            return default

# 高级PDF转Markdown转换器
class PDFToMarkdownConverter:
    """高级PDF转Markdown转换器"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logger
        self.temp_dir = config.get("general", "temp_dir")
        self.task_id = str(uuid.uuid4())[:8]
        self.task_temp_dir = os.path.join(self.temp_dir, self.task_id)
        os.makedirs(self.task_temp_dir, exist_ok=True)
        
        # 初始化OCR引擎
        self.ocr = self._init_ocr()
        self.table_ocr = self._init_table_ocr()
        
        # 性能统计
        self.stats = {
            "start_time": time.time(),
            "pages_processed": 0,
            "images_extracted": 0,
            "tables_detected": 0,
            "formulas_detected": 0,
            "errors": 0
        }
    
    def _init_ocr(self) -> PaddleOCR:
        """初始化OCR引擎"""
        ocr_config = self.config.get("ocr", {})
        return PaddleOCR(
            use_angle_cls=ocr_config.get("use_angle_cls", True),
            lang=ocr_config.get("lang", "ch"),
            use_gpu=ocr_config.get("use_gpu", False),
            use_doc_orientation_classify=ocr_config.get("use_doc_orientation_classify", False),
            use_doc_unwarping=ocr_config.get("use_doc_unwarping", False),
            use_textline_orientation=ocr_config.get("use_textline_orientation", False),
            show_log=ocr_config.get("show_log", False)
        )
    
    def _init_table_ocr(self) -> PaddleOCR:
        """初始化表格OCR引擎"""
        ocr_config = self.config.get("ocr", {})
        return PaddleOCR(
            use_angle_cls=ocr_config.get("use_angle_cls", True),
            lang=ocr_config.get("lang", "ch"),
            use_gpu=ocr_config.get("use_gpu", False),
            show_log=ocr_config.get("show_log", False)
        )
    
    def process_pdf(self, pdf_path: str, output_md_path: str) -> Dict[str, Any]:
        """
        处理PDF文件
        
        参数:
            pdf_path: PDF文件路径
            output_md_path: 输出Markdown文件路径
            
        返回:
            处理统计信息
        """
        self.logger.info(f"开始处理PDF: {pdf_path}")
        self.stats["pdf_path"] = pdf_path
        self.stats["output_path"] = output_md_path
        
        try:
            # 提取PDF内容
            elements = self.extract_pdf_content(pdf_path)
            
            # 转换为Markdown
            self.convert_to_markdown(elements, output_md_path)
            
            # 计算处理时间
            self.stats["end_time"] = time.time()
            self.stats["processing_time"] = self.stats["end_time"] - self.stats["start_time"]
            
            self.logger.info(f"PDF处理完成: {pdf_path}")
            self.logger.info(f"统计信息: {json.dumps(self.stats, indent=2, default=str)}")
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"处理PDF时发生错误: {e}")
            self.stats["errors"] += 1
            self.stats["error_message"] = str(e)
            raise
    
    def extract_pdf_content(self, pdf_path: str) -> List[Dict]:
        """提取PDF内容"""
        self.logger.info("开始提取PDF内容")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        max_pages = self.config.get("processing", "max_pages")
        skip_pages = self.config.get("processing", "skip_pages", [])
        
        if max_pages and max_pages < total_pages:
            total_pages = max_pages
        
        elements = []
        
        # 使用线程池并行处理页面
        with ThreadPoolExecutor(max_workers=self.config.get("general", "max_workers")) as executor:
            future_to_page = {
                executor.submit(self.process_page, doc, page_num): page_num 
                for page_num in range(total_pages) 
                if page_num + 1 not in skip_pages
            }
            
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_elements = future.result()
                    elements.extend(page_elements)
                    self.stats["pages_processed"] += 1
                    self.logger.info(f"已处理页面 {page_num + 1}/{total_pages}")
                except Exception as e:
                    self.logger.error(f"处理页面 {page_num + 1} 时发生错误: {e}")
                    self.stats["errors"] += 1
        
        doc.close()
        return elements
    
    def process_page(self, doc: fitz.Document, page_num: int) -> List[Dict]:
        """处理单个页面"""
        page = doc.load_page(page_num)
        elements = []
        dpi = self.config.get("processing", "dpi")
        
        # 提取文本
        if self.config.get("output", "include_text"):
            try:
                text = page.get_text("text")
                if text.strip():
                    elements.append({
                        "type": "text",
                        "content": text,
                        "page": page_num + 1
                    })
            except Exception as e:
                self.logger.warning(f"提取页面 {page_num + 1} 文本时发生错误: {e}")
        
        # 提取图像
        if self.config.get("output", "include_images"):
            try:
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 保存图像
                    image_ext = base_image["ext"]
                    image_path = os.path.join(
                        self.task_temp_dir, 
                        f"page_{page_num+1}_img_{img_index+1}.{image_ext}"
                    )
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    elements.append({
                        "type": "image",
                        "path": image_path,
                        "page": page_num + 1
                    })
                    self.stats["images_extracted"] += 1
            except Exception as e:
                self.logger.warning(f"提取页面 {page_num + 1} 图像时发生错误: {e}")
        
        # 转换为高分辨率图像用于OCR和表格检测
        try:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # 使用OpenCV处理图像
            nparr = np.frombuffer(img_data, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # 检测表格区域
            if self.config.get("output", "include_tables"):
                try:
                    tables = self.detect_tables(img_cv, page_num + 1)
                    elements.extend(tables)
                    self.stats["tables_detected"] += len(tables)
                except Exception as e:
                    self.logger.warning(f"检测页面 {page_num + 1} 表格时发生错误: {e}")
            
            # 检测数学公式区域
            if self.config.get("output", "include_formulas"):
                try:
                    formulas = self.detect_formulas(img_cv, page_num + 1)
                    elements.extend(formulas)
                    self.stats["formulas_detected"] += len(formulas)
                except Exception as e:
                    self.logger.warning(f"检测页面 {page_num + 1} 公式时发生错误: {e}")
                    
        except Exception as e:
            self.logger.warning(f"处理页面 {page_num + 1} 图像时发生错误: {e}")
        
        return elements
    
    def detect_tables(self, image: np.ndarray, page_num: int) -> List[Dict]:
        """检测图像中的表格区域"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用边缘检测和轮廓查找来检测表格
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        min_area = self.config.get("processing", "min_table_area")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # 裁剪表格区域
                table_region = image[y:y+h, x:x+w]
                
                # 保存表格图像
                table_path = os.path.join(self.task_temp_dir, f"page_{page_num}_table_{i+1}.png")
                cv2.imwrite(table_path, table_region)
                
                # 使用OCR识别表格内容
                table_content = self.recognize_table(table_region)
                
                tables.append({
                    "type": "table",
                    "path": table_path,
                    "content": table_content,
                    "page": page_num,
                    "position": (x, y, w, h)
                })
        
        return tables
    
    def recognize_table(self, table_image: np.ndarray) -> str:
        """识别表格内容"""
        try:
            # 使用PaddleOCR识别表格文本
            result = self.table_ocr.ocr(table_image, cls=True)
            
            # 提取文本和位置
            cells = []
            for line in result:
                if line and line[0]:
                    for word_info in line:
                        text = word_info[1][0]
                        bbox = word_info[0]
                        x_center = (bbox[0][0] + bbox[2][0]) / 2
                        y_center = (bbox[0][1] + bbox[2][1]) / 2
                        cells.append({
                            "text": text,
                            "x": x_center,
                            "y": y_center
                        })
            
            # 按行和列组织单元格
            if not cells:
                return "| 无法识别的表格 |\n| --- |"
            
            # 按y坐标分组行
            sorted_cells = sorted(cells, key=lambda c: c["y"])
            rows = []
            current_row = [sorted_cells[0]]
            row_threshold = self.config.get("processing", "row_threshold")
            
            for i in range(1, len(sorted_cells)):
                if abs(sorted_cells[i]["y"] - sorted_cells[i-1]["y"]) < row_threshold:
                    current_row.append(sorted_cells[i])
                else:
                    rows.append(current_row)
                    current_row = [sorted_cells[i]]
            rows.append(current_row)
            
            # 每行内按x坐标排序
            for row in rows:
                row.sort(key=lambda c: c["x"])
            
            # 生成Markdown表格
            markdown_table = ""
            for i, row in enumerate(rows):
                if i == 0:
                    # 表头
                    markdown_table += "| " + " | ".join([cell["text"] for cell in row]) + " |\n"
                    markdown_table += "| " + " | ".join(["---"] * len(row)) + " |\n"
                else:
                    # 表格内容
                    markdown_table += "| " + " | ".join([cell["text"] for cell in row]) + " |\n"
            
            return markdown_table
            
        except Exception as e:
            self.logger.warning(f"识别表格时发生错误: {e}")
            return "| 表格识别错误 |\n| --- |"
    
    def detect_formulas(self, image: np.ndarray, page_num: int) -> List[Dict]:
        """检测图像中的数学公式区域"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用二值化处理
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        formulas = []
        min_area = self.config.get("processing", "min_formula_area")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # 裁剪公式区域
                formula_region = image[y:y+h, x:x+w]
                
                # 保存公式图像
                formula_path = os.path.join(self.task_temp_dir, f"page_{page_num}_formula_{i+1}.png")
                cv2.imwrite(formula_path, formula_region)
                
                formulas.append({
                    "type": "formula",
                    "path": formula_path,
                    "page": page_num,
                    "position": (x, y, w, h)
                })
        
        return formulas
    
    def convert_to_markdown(self, elements: List[Dict], output_md_path: str) -> None:
        """将提取的元素转换为Markdown格式"""
        self.logger.info("开始转换为Markdown格式")
        
        # 按页码排序元素
        elements.sort(key=lambda x: x.get("page", 0))
        
        with open(output_md_path, 'w', encoding='utf-8') as md_file:
            current_page = 0
            
            for element in elements:
                # 添加页码标题
                if self.config.get("output", "page_headers") and element["page"] != current_page:
                    current_page = element["page"]
                    md_file.write(f"\n# 第 {current_page} 页\n\n")
                
                # 处理不同类型的元素
                try:
                    if element["type"] == "text" and self.config.get("output", "include_text"):
                        self._process_text_element(element, md_file)
                    
                    elif element["type"] == "image" and self.config.get("output", "include_images"):
                        self._process_image_element(element, md_file, output_md_path)
                    
                    elif element["type"] == "table" and self.config.get("output", "include_tables"):
                        self._process_table_element(element, md_file, output_md_path)
                    
                    elif element["type"] == "formula" and self.config.get("output", "include_formulas"):
                        self._process_formula_element(element, md_file, output_md_path)
                        
                except Exception as e:
                    self.logger.warning(f"处理元素时发生错误: {e}")
                    self.stats["errors"] += 1
    
    def _process_text_element(self, element: Dict, md_file) -> None:
        """处理文本元素"""
        text = element["content"].strip()
        if text:
            # 检测标题
            if len(text) < 50 and not text.endswith(('.', '。', '，', ',')):
                md_file.write(f"## {text}\n\n")
            else:
                # 处理段落
                paragraphs = text.split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        md_file.write(f"{para.strip()}\n\n")
    
    def _process_image_element(self, element: Dict, md_file, output_md_path: str) -> None:
        """处理图像元素"""
        rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
        md_file.write(f"![图像]({rel_path})\n\n")
    
    def _process_table_element(self, element: Dict, md_file, output_md_path: str) -> None:
        """处理表格元素"""
        md_file.write(f"**表格**\n\n")
        md_file.write(f"{element['content']}\n\n")
        
        if self.config.get("output", "table_images"):
            rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
            md_file.write(f"![表格图像]({rel_path})\n\n")
    
    def _process_formula_element(self, element: Dict, md_file, output_md_path: str) -> None:
        """处理公式元素"""
        rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
        md_file.write(f"![公式]({rel_path})\n\n")
    
    def cleanup(self) -> None:
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.task_temp_dir):
                shutil.rmtree(self.task_temp_dir)
                self.logger.info(f"已清理临时目录: {self.task_temp_dir}")
        except Exception as e:
            self.logger.warning(f"清理临时文件时发生错误: {e}")

# API服务类
class PDFConversionService:
    """PDF转换服务"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigManager(config_path)
        self.logger = logger
        self.active_tasks = {}
    
    def convert_pdf(self, pdf_path: str, output_md_path: str) -> Dict[str, Any]:
        """
        转换PDF文件
        
        参数:
            pdf_path: PDF文件路径
            output_md_path: 输出Markdown文件路径
            
        返回:
            处理统计信息
        """
        task_id = str(uuid.uuid4())[:8]
        self.active_tasks[task_id] = {
            "status": "processing",
            "start_time": datetime.now(),
            "pdf_path": pdf_path,
            "output_path": output_md_path
        }
        print("convert_pdf")
        try:
            converter = PDFToMarkdownConverter(self.config, self.logger)
            result = converter.process_pdf(pdf_path, output_md_path)
            
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["end_time"] = datetime.now()
            self.active_tasks[task_id]["result"] = result
            
            converter.cleanup()
            return result
            
        except Exception as e:
            self.active_tasks[task_id]["status"] = "failed"
            self.active_tasks[task_id]["end_time"] = datetime.now()
            self.active_tasks[task_id]["error"] = str(e)
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict:
        """获取所有任务状态"""
        return self.active_tasks

# 命令行接口
def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description="高级PDF转Markdown转换工具")
    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出Markdown文件路径")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = "DEBUG" if args.verbose else "INFO"
    
    # 初始化服务
    service = PDFConversionService(args.config)
    service.logger.setLevel(log_level)
    print(args.input)
    print(args.output)

    try:
        # 执行转换
        result = service.convert_pdf(args.input, args.output)
        print(f"转换完成! 统计信息: {json.dumps(result, indent=2, default=str)}")
        
    except Exception as e:
        service.logger.error(f"转换失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # 示例配置文件 (config.yaml)
    """
    general:
      max_workers: 4
      timeout: 3600
      temp_dir: "./temp_pdf_content"
      log_level: "INFO"
      log_file: "pdf2md.log"
    
    ocr:
      use_gpu: false
      lang: "ch"
      use_angle_cls: true
    
    processing:
      dpi: 300
      min_table_area: 5000
      min_formula_area: 100
      max_pages: null
      skip_pages: []
    
    output:
      include_images: true
      include_tables: true
      include_formulas: true
      include_text: true
      page_headers: true
      table_images: true
    """
    
    # 运行命令行接口
    exit(main())