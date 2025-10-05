from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Optional, Dict, Union
import os

def chunk_markdown_content(md_content: str, 
                          metadata: Optional[Dict] = None, 
                          chunk_size: int = 1000, 
                          chunk_overlap: int = 200) -> List[Document]:
    """
    将Markdown内容分块处理
    
    Args:
        md_content: Markdown格式的文本内容
        metadata: 元数据字典
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小
    
    Returns:
        List[Document]: 分块后的文档列表
    """
    if metadata is None:
        metadata = {}
    
    # 创建Document对象
    document = Document(page_content=md_content, metadata=metadata)
    
    # 定义Markdown标题分割器
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False  # 保留标题在内容中
    )
    
    # 按标题分割
    try:
        header_splits = markdown_splitter.split_text(document.page_content)
    except Exception as e:
        print(f"标题分割失败，使用普通分割器: {e}")
        header_splits = [document]
    
    # 保留原始元数据并与标题元数据合并
    for split in header_splits:
        split.metadata = {**document.metadata, **split.metadata}
    
    # 进一步分割大块内容
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]  # 分割符优先级
    )
  
    # 组合所有分割块
    final_chunks = []
    for split in header_splits:
        if len(split.page_content) <= chunk_size:
            # 如果内容已经小于分块大小，直接添加
            final_chunks.append(split)
        else:
            # 需要进一步分割
            chunks = text_splitter.split_documents([split])
            final_chunks.extend(chunks)
    
    return final_chunks

def chunk_markdown_from_file(file_path: str, 
                            chunk_size: int = 1000, 
                            chunk_overlap: int = 200,
                            encoding: str = 'utf-8') -> List[Document]:
    """
    从Markdown文件加载并分块
    
    Args:
        file_path: Markdown文件路径
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小
        encoding: 文件编码
    
    Returns:
        List[Document]: 分块后的文档列表
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if not file_path.endswith(('.md', '.markdown')):
        print(f"警告: 文件 {file_path} 可能不是Markdown文件")
    
    try:
        # 使用TextLoader加载文件
        loader = TextLoader(file_path, encoding=encoding)
        documents = loader.load()
        
        if not documents:
            return []
        
        # 提取元数据
        base_metadata = {
            "source": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "last_modified": os.path.getmtime(file_path)
        }
        
        # 合并加载器的元数据
        file_metadata = {**base_metadata, **documents[0].metadata}
        
        # 分块处理
        chunks = chunk_markdown_content(
            md_content=documents[0].page_content,
            metadata=file_metadata,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return chunks
        
    except Exception as e:
        print(f"文件加载失败: {e}")
        # 尝试直接读取文件
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            base_metadata = {
                "source": file_path,
                "file_name": os.path.basename(file_path),
                "error": f"Loader failed: {str(e)}"
            }
            
            return chunk_markdown_content(
                md_content=content,
                metadata=base_metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        except Exception as inner_e:
            raise Exception(f"无法处理文件 {file_path}: {inner_e}")

def chunk_markdown_from_directory(directory_path: str,
                                 chunk_size: int = 1000,
                                 chunk_overlap: int = 200,
                                 encoding: str = 'utf-8') -> List[Document]:
    """
    处理目录中的所有Markdown文件
    
    Args:
        directory_path: 目录路径
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小
        encoding: 文件编码
    
    Returns:
        List[Document]: 所有文件的分块文档列表
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"目录不存在: {directory_path}")
    
    if not os.path.isdir(directory_path):
        raise ValueError(f"路径不是目录: {directory_path}")
    
    all_chunks = []
    
    # 遍历目录中的所有.md和.markdown文件
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(('.md', '.markdown')):
                file_path = os.path.join(root, file)
                try:
                    chunks = chunk_markdown_from_file(
                        file_path, chunk_size, chunk_overlap, encoding
                    )
                    all_chunks.extend(chunks)
                    print(f"成功处理: {file_path} ({len(chunks)} 个分块)")
                except Exception as e:
                    print(f"处理文件失败 {file_path}: {e}")
    
    return all_chunks

# 示例用法
if __name__ == "__main__":
  
    # 示例2: 从文件处理
    print("\n=================== 示例2: 从文件处理 ===")
    # 创建一个示例Markdown文件
    sample_file = "/Users/luoqi/Downloads/math-test-new_MinerU__20250918125817.md"
    #with open(sample_file, 'w', encoding='utf-8') as f:
    #    f.write(sample_md_content)
    
    try:
        file_chunks = chunk_markdown_from_file(sample_file)
        print(f"从文件生成了 {len(file_chunks)} 个分块")
        print("="*50)
        for i, chunk in enumerate(file_chunks):
            print(f"\nChunk {i + 1}:")
            print(f"Metadata: {chunk.metadata}")
            print(f"Content: {chunk.page_content[:200]}...")
        
        #print({str(file_chunks)})
        # 清理示例文件
       # os.remove(sample_file)
        
    except Exception as e:
        print(f"文件处理示例失败: {e}")
    
    '''
    # 示例3: 处理目录
    print("\n=== 示例3: 处理目录 ===")
    # 创建示例目录和文件
    sample_dir = "sample_docs"
    os.makedirs(sample_dir, exist_ok=True)
    
    for i in range(3):
        with open(os.path.join(sample_dir, f"doc_{i}.md"), 'w', encoding='utf-8') as f:
            f.write(f"# Document {i}\n\nContent for document {i}")
    
    try:
        dir_chunks = chunk_markdown_from_directory(sample_dir)
        print(f"从目录生成了 {len(dir_chunks)} 个分块")
        
        # 清理示例目录
        import shutil
        shutil.rmtree(sample_dir)
        
    except Exception as e:
        print(f"目录处理示例失败: {e}")
    '''
    