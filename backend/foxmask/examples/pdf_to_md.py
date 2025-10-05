import os
import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import cv2
import numpy as np
from PIL import Image
import re
from typing import List, Tuple
import argparse

class PDFToMarkdownConverter:
    def __init__(self, use_gpu=False):
        """
        初始化OCR引擎
        """
        self.ocr = PaddleOCR(
            use_angle_cls=True,    # 启用方向分类，对PDF很有用
            lang='ch',             # 中文模型
            use_gpu=use_gpu,       # 是否使用GPU
            det_limit_side_len=1280,  # 限制图像尺寸，平衡精度和速度
            rec_batch_num=2,       # 识别批次大小
            show_log=False         # 关闭详细日志
        )
        print("PaddleOCR 初始化完成")

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[np.ndarray]:
        """
        将PDF每一页转换为图像
        """
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(dpi / 72, dpi / 72)  # 设置分辨率
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # 转换为OpenCV格式
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                images.append(img)
                
            doc.close()
            print(f"成功转换 {len(images)} 页PDF为图像")
            return images
        except Exception as e:
            print(f"PDF转换失败: {e}")
            return []

    def is_title(self, text: str, confidence: float, bbox: List[Tuple[int, int]]) -> bool:
        """
        启发式规则判断是否为标题
        """
        # 规则1: 文本较短且置信度高
        if len(text) < 20 and confidence > 0.9:
            return True
        
        # 规则2: 包含常见标题关键词（可扩展）
        title_keywords = ['目录', '摘要', '引言', '背景', '方法', '结果', '讨论', '结论', '参考文献', '附录']
        if any(keyword in text for keyword in title_keywords):
            return True
            
        # 规则3: 文本位置在页面顶部
        if bbox and bbox[0][1] < 100:  # y坐标小于100像素
            return True
            
        return False

    def is_list_item(self, text: str) -> bool:
        """
        判断是否为列表项
        """
        # 匹配数字列表: 1., 2., 3. 等
        if re.match(r'^(\d+[\.\)]|[-•*])\s', text.strip()):
            return True
        # 匹配中文数字列表: 一、, 二、, 等
        if re.match(r'^[一二三四五六七八九十]+[、.]\s', text.strip()):
            return True
        return False

    def process_ocr_results(self, ocr_result, img_width: int) -> str:
        """
        处理OCR结果，生成Markdown格式
        """
        if not ocr_result or not ocr_result[0]:
            return ""
            
        md_lines = []
        previous_y = -1
        in_list = False
        
        for line in ocr_result[0]:
            if not line or len(line) < 2:
                continue
                
            bbox, (text, confidence) = line[:2]
            text = text.strip()
            
            if not text:
                continue
                
            # 计算文本块的中心y坐标
            if bbox:
                y_center = sum(point[1] for point in bbox) / len(bbox)
            else:
                y_center = previous_y + 50  # 默认值
                
            # 检测换行（基于y坐标的变化）
            if previous_y != -1 and abs(y_center - previous_y) > 30:
                if in_list:
                    md_lines.append('')  # 列表结束
                    in_list = False
                else:
                    md_lines.append('')  # 普通换行
                    
            # 判断文本类型并转换为Markdown
            if self.is_title(text, confidence, bbox):
                # 简单标题检测，可以根据需要增强
                md_lines.append(f"## {text}")
            elif self.is_list_item(text):
                if not in_list:
                    in_list = True
                # 清理列表标记
                clean_text = re.sub(r'^(\d+[\.\)]|[-•*]|[一二三四五六七八九十]+[、.])\s*', '', text)
                md_lines.append(f"- {clean_text}")
            elif text.startswith('图') or text.startswith('表'):
                # 图表标题
                md_lines.append(f"**{text}**")
            elif len(text) > 50:  # 长段落
                md_lines.append(text)
            else:  # 短文本行
                md_lines.append(text)
                
            previous_y = y_center
            
        return '\n'.join(md_lines)

    def convert_pdf_to_markdown(self, pdf_path: str, output_md_path: str = None, dpi: int = 200):
        """
        主转换函数
        """
        if not output_md_path:
            output_md_path = pdf_path.replace('.pdf', '.md')
            if output_md_path == pdf_path:  # 如果没有.pdf后缀
                output_md_path += '.md'
        
        # 1. PDF转图像
        print("正在转换PDF为图像...")
        images = self.pdf_to_images(pdf_path, dpi)
        if not images:
            return False
            
        all_md_content = []
        
        # 2. 逐页处理
        for page_num, img in enumerate(images, 1):
            print(f"正在处理第 {page_num} 页...")
            
            # 3. OCR识别
            result = self.ocr.ocr(img, cls=True)
            
            # 4. 转换为Markdown
            md_content = self.process_ocr_results(result, img.shape[1])
            
            if md_content.strip():
                # 添加分页符和页码
                all_md_content.append(f"---\n\n### 第 {page_num} 页\n\n")
                all_md_content.append(md_content)
                all_md_content.append("\n\n")  # 添加额外空行
        
        # 5. 保存结果
        if all_md_content:
            final_md = ''.join(all_md_content)
            
            # 后处理：清理多余的空白行
            final_md = re.sub(r'\n{3,}', '\n\n', final_md)
            
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write(final_md)
            
            print(f"转换完成！Markdown文件已保存至: {output_md_path}")
            print(f"总页数: {len(images)}")
            return True
        else:
            print("未识别到任何文本内容")
            return False

def main():
    parser = argparse.ArgumentParser(description='将PDF转换为Markdown格式')
    parser.add_argument('input_pdf', help='输入的PDF文件路径')
    parser.add_argument('-o', '--output', help='输出的Markdown文件路径')
    parser.add_argument('--dpi', type=int, default=200, help='图像分辨率（默认200）')
    parser.add_argument('--gpu', action='store_true', help='使用GPU加速')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.input_pdf):
        print(f"错误：文件 {args.input_pdf} 不存在")
        return
    
    # 创建转换器实例
    converter = PDFToMarkdownConverter(use_gpu=args.gpu)
    
    # 执行转换
    success = converter.convert_pdf_to_markdown(
        pdf_path=args.input_pdf,
        output_md_path=args.output,
        dpi=args.dpi
    )
    
    if success:
        print("✅ 转换成功！")
    else:
        print("❌ 转换失败")

if __name__ == "__main__":
    main()