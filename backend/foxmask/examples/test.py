import os
import requests
import tempfile
import base64
import time
import fitz
from PIL import Image
import io

def pdf_to_markdown_simple(pdf_path, output_md_path=None, pages_to_process=3):
    """
    简化版的PDF转Markdown函数
    """
    # 模型名称（根据您的ollama ls输出）
    MODEL_NAME = "yasserrmd/Nanonets-OCR-s:latest"
    BASE_URL = "http://localhost:11434"
    
    # 检查Ollama服务
    try:
        response = requests.get(f"{BASE_URL}/api/tags", timeout=10000)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        if MODEL_NAME not in model_names:
            print(f"错误: 模型 {MODEL_NAME} 未找到")
            print(f"可用模型: {model_names}")
            return None
    except:
        print("Ollama服务未启动，请运行: ollama serve")
        return None
    
    # 处理PDF
    print(f"使用模型: {MODEL_NAME}")
    print("开始处理PDF...")
    
    # 转换为图像
    images = []
    pdf_document = fitz.open(pdf_path)
    
    for page_num in range(min(pages_to_process, len(pdf_document))):
        page = pdf_document.load_page(page_num)
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
        print(f"已转换第 {page_num + 1} 页")
    
    pdf_document.close()
    
    # 处理图像
    all_markdown = []
    
    for i, image in enumerate(images):
        print(f"处理第 {i + 1}/{len(images)} 页...")
        
        # 转换为base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # 提示词
        prompt = """Extract text from this mathematics textbook page and convert to Markdown format. 
        Focus on accurate LaTeX for equations, proper heading structure, and table conversion."""
        
        # 调用API
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/generate",
                json=payload,
                timeout=30000
            )
            response.raise_for_status()
            
            result = response.json()
            if "response" in result:
                all_markdown.append(f"\n\n--- Page {i+1} ---\n\n")
                all_markdown.append(result["response"])
                print(f"第 {i + 1} 页处理成功")
            else:
                print(f"第 {i + 1} 页处理失败: {result}")
                
        except Exception as e:
            print(f"第 {i + 1} 页处理错误: {e}")
        
        time.sleep(1)
    
    # 保存结果
    full_markdown = "".join(all_markdown)
    
    if output_md_path:
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(full_markdown)
        print(f"结果已保存到: {output_md_path}")
    
    return full_markdown

# 使用示例
if __name__ == "__main__":
    pdf_path = "/Users/luoqi/Downloads/高中-数学/沪教版-上海教育出版社/普通高中教科书·数学选择性必修 第一册.pdf"
    output_path = "数学教材_测试.md"
    
    result = pdf_to_markdown_simple(pdf_path, output_path, pages_to_process=10)
    
    if result:
        print("\n处理完成！")
        print(f"结果长度: {len(result)} 字符")
        print(f"前500字符预览:")
        print(result[:500] + "..." if len(result) > 500 else result)