
# 仅替换与 LaTeX 解析相关的部分，其他部分保持不变
import os
import fitz
import cv2
import numpy as np
import logging
import json
import time
import uuid
import re
import shutil
import requests
from datetime import datetime
from PIL import Image
from paddleocr import PaddleOCR
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import argparse
import yaml

# 设置日志系统（与原代码相同）
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger("pdf2md")
    logger.setLevel(getattr(logging, log_level.upper()))
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

# 配置管理（与原代码相同）
class ConfigManager:
    DEFAULT_CONFIG = {
        "general": {"max_workers": 4, "timeout": 3600, "temp_dir": "./temp_pdf_content", "log_level": "INFO", "log_file": None},
        "ocr": {"use_gpu": False, "lang": "ch", "use_angle_cls": True, "show_log": False},
        "processing": {"dpi": 150, "min_table_area": 5000, "min_formula_area": 100, "row_threshold": 20, "max_pages": 500, "skip_pages": []},
        "output": {"include_images": True, "include_tables": True, "include_formulas": True, "include_text": True, "page_headers": True, "table_images": True},
        "mathpix": {"app_id": None, "app_key": None}  # 新增 Mathpix API 配置
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def load_config(self, config_path: str):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._deep_update(self.config, yaml.safe_load(f))
        except Exception as e:
            logging.warning(f"加载配置文件失败: {e}，使用默认配置")

    def _deep_update(self, original: Dict, update: Dict):
        for key, value in update.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.config.get(section, {}).get(key, default)

# LaTeX 格式化器
class LaTeXFormatter:
    def __init__(self):
        # 扩展的正则表达式，识别更多 LaTeX 模式
        self.latex_patterns = [
            (r"(\d+/\d+)", r"\\frac{\1}"),  # 分数：1/2 -> \frac{1}{2}
            (r"\^(\d+|[a-zA-Z]+)", r"^{\1}"),  # 上标：x^2 -> x^{2}
            (r"_(\d+|[a-zA-Z]+)", r"_{\1}"),  # 下标：x_1 -> x_{1}
            (r"sqrt\[(\d+)\]([a-zA-Z0-9]+)", r"\\sqrt[\1]{\2}"),  # 根号：sqrt[2]{x} -> \sqrt[2]{x}
            (r"sum_([a-zA-Z0-9]+)\^([a-zA-Z0-9]+)", r"\\sum_{\1}^{\2}"),  # 求和：sum_i^n -> \sum_{i}^{n}
            (r"int_([a-zA-Z0-9]+)\^([a-zA-Z0-9]+)", r"\\int_{\1}^{\2}"),  # 积分：int_a^b -> \int_{a}^{b}
            (r"([a-zA-Z]+)\(([a-zA-Z0-9]+)\)", r"\\%s{\2}"),  # 函数：sin(x) -> \sin{x}
            (r"[+\-*/=()[\]\{\}]|\d+[a-zA-Z]|[a-zA-Z]+\d", None)  # 基本数学符号和混合表达式
        ]

    def format_latex(self, text: str) -> str:
        """格式化文本为 LaTeX"""
        try:
            for pattern, replacement in self.latex_patterns:
                if replacement:
                    text = re.sub(pattern, replacement, text)
            # 清理多余空格并确保 LaTeX 语法正确
            text = text.strip().replace("  ", " ")
            return f"$${text}$$"
        except Exception as e:
            logging.warning(f"LaTeX 格式化错误: {e}")
            return f"$${text}$$"

# PDF 转 Markdown 转换器
class AdvancedPDFToMarkdownConverter:
    def __init__(self, config: ConfigManager, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.temp_dir = config.get("general", "temp_dir")
        self.task_id = str(uuid.uuid4())[:8]
        self.task_temp_dir = os.path.join(self.temp_dir, self.task_id)
        os.makedirs(self.task_temp_dir, exist_ok=True)
        self.ocr = self._init_ocr()
        self.latex_formatter = LaTeXFormatter()
        self.stats = {
            "start_time": time.time(), "pages_processed": 0, "images_extracted": 0,
            "tables_detected": 0, "formulas_detected": 0, "errors": 0,
            "pdf_path": "", "output_path": ""
        }

    def _init_ocr(self) -> PaddleOCR:
        try:
            ocr_config = {
                "use_angle_cls": self.config.get("ocr", "use_angle_cls", True),
                "lang": self.config.get("ocr", "lang", "ch"),
                "use_gpu": self.config.get("ocr", "use_gpu", False),
                "show_log": self.config.get("ocr", "show_log", False)
            }
            return PaddleOCR(**ocr_config)
        except Exception as e:
            self.logger.error(f"初始化OCR引擎失败: {e}")
            return PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)

    def process_pdf(self, pdf_path: str, output_md_path: str) -> Dict[str, Any]:
        self.logger.info(f"开始处理PDF: {pdf_path}")
        self.stats["pdf_path"] = pdf_path
        self.stats["output_path"] = output_md_path
        try:
            elements = self.extract_pdf_content(pdf_path)
            self.convert_to_markdown(elements, output_md_path)
            self.stats["end_time"] = time.time()
            self.stats["processing_time"] = self.stats["end_time"] - self.stats["start_time"]
            self.logger.info(f"PDF处理完成: {pdf_path}")
            return self._get_serializable_stats()
        except Exception as e:
            self.logger.error(f"处理PDF时发生错误: {e}")
            self.stats["errors"] += 1
            self.stats["error_message"] = str(e)
            raise
        finally:
            self.cleanup()

    def _get_serializable_stats(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id, "pdf_path": self.stats["pdf_path"], "output_path": self.stats["output_path"],
            "pages_processed": self.stats["pages_processed"], "images_extracted": self.stats["images_extracted"],
            "tables_detected": self.stats["tables_detected"], "formulas_detected": self.stats["formulas_detected"],
            "errors": self.stats["errors"], "processing_time": round(self.stats.get("processing_time", 0), 2),
            "start_time": datetime.fromtimestamp(self.stats["start_time"]).isoformat(),
            "end_time": datetime.fromtimestamp(self.stats.get("end_time", time.time())).isoformat()
        }

    def extract_pdf_content(self, pdf_path: str) -> List[Dict]:
        self.logger.info("开始提取PDF内容")
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), self.config.get("processing", "max_pages"))
        skip_pages = self.config.get("processing", "skip_pages", [])
        elements = []
        
        with ThreadPoolExecutor(max_workers=self.config.get("general", "max_workers")) as executor:
            future_to_page = {executor.submit(self.process_page, doc, page_num): page_num for page_num in range(total_pages) if page_num + 1 not in skip_pages}
            for future in as_completed(future_to_page):
                try:
                    page_elements = future.result()
                    elements.extend(page_elements)
                    self.stats["pages_processed"] += 1
                    self.logger.info(f"已处理页面 {future_to_page[future] + 1}/{total_pages}")
                except Exception as e:
                    self.logger.error(f"处理页面 {future_to_page[future] + 1} 时发生错误: {e}")
                    self.stats["errors"] += 1
        
        doc.close()
        return sorted(elements, key=lambda x: x.get("page", 0))

    def process_page(self, doc: fitz.Document, page_num: int) -> List[Dict]:
        elements = []
        page = doc.load_page(page_num)
        dpi = self.config.get("processing", "dpi")
        
        try:
            if self.config.get("output", "include_text"):
                text = page.get_text("text")
                if text.strip():
                    elements.append({"type": "text", "content": text, "page": page_num + 1})

            if self.config.get("output", "include_images"):
                for img_index, img in enumerate(page.get_images()):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_path = os.path.join(self.task_temp_dir, f"page_{page_num+1}_img_{img_index+1}.{base_image['ext']}")
                    with open(image_path, "wb") as f:
                        f.write(base_image["image"])
                    elements.append({"type": "image", "path": image_path, "page": page_num + 1})
                    self.stats["images_extracted"] += 1

            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            img_data = pix.tobytes("png")
            pix = None  # 释放内存
            nparr = np.frombuffer(img_data, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if self.config.get("output", "include_tables"):
                tables = self.detect_tables(img_cv, page_num + 1)
                elements.extend(tables)
                self.stats["tables_detected"] += len(tables)

            if self.config.get("output", "include_formulas"):
                formulas = self.detect_formulas(img_cv, page_num + 1)
                elements.extend(formulas)
                self.stats["formulas_detected"] += len(formulas)

        except Exception as e:
            self.logger.warning(f"处理页面 {page_num + 1} 时发生错误: {e}")
            self.stats["errors"] += 1

        return elements

    def detect_tables(self, image: np.ndarray, page_num: int) -> List[Dict]:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            tables = []
            min_area = self.config.get("processing", "min_table_area")

            for i, contour in enumerate(contours):
                if cv2.contourArea(contour) > min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    table_region = image[y:y+h, x:x+w]
                    table_path = os.path.join(self.task_temp_dir, f"page_{page_num}_table_{i+1}.png")
                    cv2.imwrite(table_path, table_region)
                    table_content = self.recognize_table(table_region)
                    tables.append({"type": "table", "path": table_path, "content": table_content, "page": page_num, "position": (x, y, w, h)})
            
            return tables
        except Exception as e:
            self.logger.warning(f"检测表格时发生错误: {e}")
            return []

    def recognize_table(self, table_image: np.ndarray) -> str:
        try:
            result = self.ocr.ocr(table_image, cls=True)
            if not result or not result[0]:
                return "| 无法识别的表格 |\n| --- |"
            
            cells = [
                {"text": word_info[1][0], "x": (word_info[0][0][0] + word_info[0][2][0]) / 2, "y": (word_info[0][0][1] + word_info[0][2][1]) / 2}
                for line in result for word_info in line if word_info
            ]
            
            if not cells:
                return "| 无法识别的表格 |\n| --- |"
            
            sorted_cells = sorted(cells, key=lambda c: c["y"])
            rows, current_row = [], [sorted_cells[0]]
            row_threshold = self.config.get("processing", "row_threshold")
            
            for i in range(1, len(sorted_cells)):
                if abs(sorted_cells[i]["y"] - sorted_cells[i-1]["y"]) < row_threshold:
                    current_row.append(sorted_cells[i])
                else:
                    rows.append(sorted(current_row, key=lambda c: c["x"]))
                    current_row = [sorted_cells[i]]
            rows.append(sorted(current_row, key=lambda c: c["x"]))
            
            markdown_table = "| " + " | ".join([cell["text"] for cell in rows[0]]) + " |\n" + "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
            for row in rows[1:]:
                markdown_table += "| " + " | ".join([cell["text"] for cell in row]) + " |\n"
            
            return markdown_table
        except Exception as e:
            self.logger.warning(f"识别表格时发生错误: {e}")
            return "| 表格识别错误 |\n| --- |"

    def detect_formulas(self, image: np.ndarray, page_num: int) -> List[Dict]:
        try:
            # 使用 PaddleOCR 进行文本检测
            result = self.ocr.ocr(image, cls=True)
            formulas = []
            min_area = self.config.get("processing", "min_formula_area")
            app_id = self.config.get("mathpix", "app_id")
            app_key = self.config.get("mathpix", "app_key")

            for line in result:
                for word_info in line:
                    text = word_info[1][0]
                    bbox = word_info[0]
                    area = (bbox[2][0] - bbox[0][0]) * (bbox[2][1] - bbox[0][1])
                    # 检测潜在的数学公式
                    is_formula = area > min_area and any(
                        re.search(pattern, text) for pattern, _ in self.latex_formatter.latex_patterns
                    )
                    if is_formula:
                        x, y, w, h = int(bbox[0][0]), int(bbox[0][1]), int(bbox[2][0] - bbox[0][0]), int(bbox[2][1] - bbox[0][1])
                        formula_region = image[y:y+h, x:x+w]
                        formula_path = os.path.join(self.task_temp_dir, f"page_{page_num}_formula_{len(formulas)+1}.png")
                        cv2.imwrite(formula_path, formula_region)

                        # 使用 Mathpix API（如果配置）或本地格式化
                        if app_id and app_key:
                            try:
                                latex_text = self._call_mathpix_api(formula_region, app_id, app_key)
                            except Exception as e:
                                self.logger.warning(f"Mathpix API 调用失败: {e}，使用本地格式化")
                                latex_text = self.latex_formatter.format_latex(text)
                        else:
                            latex_text = self.latex_formatter.format_latex(text)

                        formulas.append({
                            "type": "formula",
                            "path": formula_path,
                            "content": latex_text,
                            "page": page_num,
                            "position": (x, y, w, h)
                        })
            
            return formulas
        except Exception as e:
            self.logger.warning(f"检测公式时发生错误: {e}")
            return []

    def _call_mathpix_api(self, image: np.ndarray, app_id: str, app_key: str) -> str:
        """调用 Mathpix API 转换图像为 LaTeX"""
        try:
            # 将图像转换为 base64
            _, buffer = cv2.imencode(".png", image)
            import base64
            img_base64 = base64.b64encode(buffer).decode("utf-8")
            
            headers = {
                "app_id": app_id,
                "app_key": app_key,
                "Content-Type": "application/json"
            }
            data = {
                "src": f"data:image/png;base64,{img_base64}",
                "formats": ["latex_simplified"]
            }
            response = requests.post("https://api.mathpix.com/v3/text", json=data, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            return f"$${result.get('latex_simplified', '')}$$"
        except Exception as e:
            self.logger.error(f"Mathpix API 错误: {e}")
            raise

    def convert_to_markdown(self, elements: List[Dict], output_md_path: str):
        self.logger.info("开始转换为Markdown格式")
        with open(output_md_path, 'w', encoding='utf-8') as md_file:
            current_page = 0
            for element in elements:
                if self.config.get("output", "page_headers") and element["page"] != current_page:
                    current_page = element["page"]
                    md_file.write(f"\n# 第 {current_page} 页\n\n")
                
                try:
                    if element["type"] == "text" and self.config.get("output", "include_text"):
                        text = element["content"].strip()
                        if text:
                            if len(text) < 50 and not text.endswith(('.', '。', '，', ',')):
                                md_file.write(f"## {text}\n\n")
                            else:
                                for para in text.split('\n\n'):
                                    if para.strip():
                                        md_file.write(f"{para.strip()}\n\n")
                    
                    elif element["type"] == "image" and self.config.get("output", "include_images"):
                        rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
                        md_file.write(f"![图像]({rel_path})\n\n")
                    
                    elif element["type"] == "table" and self.config.get("output", "include_tables"):
                        md_file.write(f"**表格**\n\n{element['content']}\n\n")
                        if self.config.get("output", "table_images"):
                            rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
                            md_file.write(f"![表格图像]({rel_path})\n\n")
                    
                    elif element["type"] == "formula" and self.config.get("output", "include_formulas"):
                        md_file.write(f"{element['content']}\n\n")
                        rel_path = os.path.relpath(element["path"], os.path.dirname(output_md_path))
                        md_file.write(f"![公式图像]({rel_path})\n\n")
                
                except Exception as e:
                    self.logger.warning(f"处理元素时发生错误: {e}")
                    self.stats["errors"] += 1

    def cleanup(self):
        try:
            if os.path.exists(self.task_temp_dir):
                shutil.rmtree(self.task_temp_dir)
                self.logger.info(f"已清理临时目录: {self.task_temp_dir}")
        except Exception as e:
            self.logger.warning(f"清理临时文件时发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(description="PDF转Markdown转换工具（支持LaTeX解析）")
    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出Markdown文件路径")
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    config = ConfigManager(args.config)
    logger = setup_logging(log_level, config.get("general", "log_file"))
    
    try:
        converter = AdvancedPDFToMarkdownConverter(config, logger)
        result = converter.process_pdf(args.input, args.output)
        print(f"转换完成！\n统计信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return 0
    except Exception as e:
        logger.error(f"转换失败: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
