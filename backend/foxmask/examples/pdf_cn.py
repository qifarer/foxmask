import os
import requests
import tempfile
import base64
import time
import argparse
import fitz  # PyMuPDF
from PIL import Image
import io
import re

class OllamaChineseClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def generate(self, model, prompt, images=None, options=None):
        """
        调用 Ollama 的生成 API（支持中文）
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if images:
            payload["images"] = images
            
        if options:
            payload["options"] = options
            
        try:
            response = self.session.post(url, json=payload, timeout=600)  # 10分钟超时
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API 请求错误: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误详情: {e.response.text}")
            return None
    
    def is_model_available(self, model_name):
        """检查模型是否可用（支持模糊匹配）"""
        url = f"{self.base_url}/api/tags"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # 查找包含关键字的模型
            for model in models:
                if "Nanonets" in model["name"] or "OCR" in model["name"]:
                    return model["name"]
            return None
        except requests.exceptions.RequestException:
            return None

def pdf_to_images(pdf_path, dpi=300):
    """
    将 PDF 文件的每一页转换为高质量的图像（支持中文）
    """
    images = []
    
    try:
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        
        # 逐页转换
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 缩放矩阵
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为PIL图像
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
            
        pdf_document.close()
        return images
        
    except Exception as e:
        print(f"PDF转换错误: {e}")
        return []

def image_to_base64(img):
    """将PIL图像转换为base64编码字符串"""
    try:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    except Exception as e:
        print(f"图像编码错误: {e}")
        return None

def create_chinese_prompt():
    """
    创建针对中文数学教材的优化提示词
    """
    return """你是一个专业的中文文档处理助手。请将以下中文数学教材页面转换为结构化的Markdown格式。

【重要要求】：
1. 语言：全部使用中文输出，保持原文的中文内容
2. 数学公式：使用LaTeX格式，$$...$$表示块级公式，$...$表示行内公式
3. 章节结构：使用#、##、###等标题级别保持原结构
4. 表格：转换为Markdown表格格式或HTML表格
5. 特殊符号：正确识别中文标点符号和数学符号
6. 排版：保持原文的层次结构和逻辑关系

【处理指南】：
- 标题：使用适当的Markdown标题级别
- 正文：保持段落结构，使用正确的中文标点
- 公式：所有数学公式必须用LaTeX准确表示
- 例题：标记为【例题】或使用粗体
- 习题：标记为【练习】或【习题】
- 图表：添加适当的描述，使用![描述](图像)格式或HTML img标签
- 页眉页脚：忽略或适当处理

请输出整洁、结构化的中文Markdown文档。"""

def process_image_with_retry(client, image, model_name, prompt, max_retries=3):
    """
    带重试机制的处理函数（支持中文）
    """
    for attempt in range(max_retries):
        try:
            # 将图像转换为base64
            image_base64 = image_to_base64(image)
            if not image_base64:
                print("图像编码失败")
                return None
            
            # 调用Ollama API
            result = client.generate(
                model=model_name,
                prompt=prompt,
                images=[image_base64],
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_ctx": 4096,
                    "top_k": 40
                }
            )
            
            if result and "response" in result:
                return result["response"]
            else:
                print(f"第{attempt+1}次尝试失败: {result}")
                
        except Exception as e:
            print(f"第{attempt+1}次尝试错误: {e}")
        
        # 指数退避
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            print(f"等待{wait_time}秒后重试...")
            time.sleep(wait_time)
    
    print("达到最大重试次数，处理失败")
    return None

def post_process_markdown(markdown_content):
    """
    对输出的Markdown进行后处理（优化中文格式）
    """
    if not markdown_content:
        return ""
    
    # 清理多余的换行
    content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    # 确保中文标点符号正确
    content = content.replace(' ,', '，').replace(' .', '。')
    
    # 修复可能的中英文混排问题
    content = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', content)
    content = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', content)
    
    return content

def pdf_to_markdown_chinese(pdf_path, output_md_path=None, dpi=300, start_page=1, end_page=None, max_pages=None):
    """
    中文PDF转Markdown主函数
    """
    # 初始化客户端
    client = OllamaChineseClient()
    
    # 检查模型
    model_name = client.is_model_available("Nanonets-OCR-s")
    if not model_name:
        print("错误: 未找到Nanonets-OCR模型")
        print("请使用 'ollama pull yasserrmd/Nanonets-OCR-s' 下载模型")
        return None
    
    print(f"使用模型: {model_name}")
    print("开始处理中文PDF...")
    
    # 转换为图像
    print("将PDF转换为图像...")
    images = pdf_to_images(pdf_path, dpi)
    if not images:
        print("PDF转换失败")
        return None
    
    # 限制处理页面范围
    total_pages = len(images)
    if end_page is None:
        end_page = total_pages
    if max_pages:
        end_page = min(start_page + max_pages - 1, total_pages)
    
    images = images[start_page-1:end_page]
    
    # 创建中文提示词
    chinese_prompt = create_chinese_prompt()
    
    all_markdown = []
    processed_count = 0
    
    # 逐页处理
    for i, image in enumerate(images):
        actual_page = start_page + i
        print(f"处理第 {actual_page}/{total_pages} 页...")
        
        markdown_content = process_image_with_retry(client, image, model_name, chinese_prompt)
        
        if markdown_content:
            # 后处理
            processed_content = post_process_markdown(markdown_content)
            
            # 添加分页标记
            all_markdown.append(f"\n\n--- 第 {actual_page} 页 ---\n\n")
            all_markdown.append(processed_content)
            
            processed_count += 1
            print(f"第 {actual_page} 页处理成功")
            
            # 保存中间结果（每处理5页保存一次）
            if processed_count % 5 == 0 and output_md_path:
                temp_output = output_md_path.replace('.md', f'_temp_{processed_count}.md')
                with open(temp_output, 'w', encoding='utf-8') as f:
                    f.write("".join(all_markdown))
                print(f"已保存临时结果到: {temp_output}")
        else:
            print(f"第 {actual_page} 页处理失败")
        
        # 添加延迟避免过载
        time.sleep(2)
    
    # 合并结果
    full_markdown = "".join(all_markdown)
    
    # 保存最终结果
    if output_md_path and full_markdown:
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(full_markdown)
        print(f"Markdown 文件已保存至: {output_md_path}")
        print(f"成功处理 {processed_count}/{len(images)} 页")
    
    return full_markdown

def test_chinese_support():
    """测试中文支持"""
    client = OllamaChineseClient()
    
    # 测试简单中文请求
    test_prompt = "请用中文回答：你好吗？"
    
    result = client.generate(
        model="yasserrmd/Nanonets-OCR-s:latest",
        prompt=test_prompt,
        options={"temperature": 0.1}
    )
    
    if result and "response" in result:
        response = result["response"]
        print("中文支持测试成功!")
        print(f"模型响应: {response}")
        return True
    else:
        print("中文支持测试失败")
        return False

if __name__ == "__main__":
    # 测试中文支持
    print("测试中文支持...")
    if not test_chinese_support():
        print("警告: 中文支持测试失败，但将继续处理")
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="中文PDF转Markdown工具")
    parser.add_argument("input_pdf", help="输入的PDF文件路径")
    parser.add_argument("-o", "--output", help="输出的Markdown文件路径")
    parser.add_argument("--dpi", type=int, default=300, help="图像分辨率")
    parser.add_argument("--start", type=int, default=1, help="起始页码")
    parser.add_argument("--end", type=int, help="结束页码")
    parser.add_argument("--max-pages", type=int, help="最大处理页数")
    
    args = parser.parse_args()
    
    # 执行转换
    result = pdf_to_markdown_chinese(
        args.input_pdf,
        args.output,
        args.dpi,
        args.start,
        args.end,
        args.max_pages
    )
    
    if result:
        print("\n处理完成!")
        print(f"输出长度: {len(result)} 字符")
        print("\n预览前500字符:")
        print("=" * 50)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("=" * 50)
    else:
        print("处理失败")