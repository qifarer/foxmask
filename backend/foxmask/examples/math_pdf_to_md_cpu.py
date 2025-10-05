import os
import fitz  # PyMuPDF
from paddleocr import PaddleOCR

def pdf_to_markdown(pdf_path, output_md_path, dpi=200):
    """
    将PDF转换为Markdown
    
    参数:
        pdf_path: PDF文件路径
        output_md_path: 输出Markdown文件路径
        dpi: 图像分辨率(越高越清晰但处理越慢)
    """
    # 创建临时文件夹存放图像
    temp_dir = "temp_pdf_images"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 1. PDF转图像
        print("正在转换PDF为图像...")
        doc = fitz.open(pdf_path)
        image_paths = []
        
        for page_num in range(min(500,len(doc))):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            image_path = os.path.join(temp_dir, f"page_{page_num+1:03d}.png")
            pix.save(image_path)
            image_paths.append(image_path)
            
        doc.close()
        
        # 2. 初始化PaddleOCR
        print("正在初始化OCR引擎...")
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            use_gpu=False,  # 不使用GPU加速
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        
        # 3. 处理每页图像并生成Markdown
        print("正在识别文本并生成Markdown...")
        with open(output_md_path, 'w', encoding='utf-8') as md_file:
            md_file.write("# PDF转换结果\n\n")
            
            for i, image_path in enumerate(image_paths):
                md_file.write(f"## 第 {i+1} 页\n\n")
                print(f"处理第 {i+1}/{len(image_paths)} 页...")
                
                # 执行OCR
                result = ocr.ocr(image_path, cls=True)
                
                # 提取文本
                if result and result[0]:
                    for line in result[0]:
                        if line and line[1]:
                            text = line[1][0]
                            md_file.write(text + "\n")
                
                md_file.write("\n\n")
        
        print(f"转换完成! Markdown文件已保存至: {output_md_path}")
        
    finally:
        # 清理临时文件
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    # 使用示例
    pdf_path = "/Users/luoqi/Downloads/高中-数学/沪教版-上海教育出版社/普通高中教科书·数学选择性必修 第一册.pdf"
    output_md_path = "/Users/luoqi/Downloads/高中数学选择性必修第一册-1.md"
    
    pdf_to_markdown(pdf_path, output_md_path, dpi=200)