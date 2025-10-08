import copy
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

from loguru import logger

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path
from foxmask.utils.minio_client import minio_client
from foxmask.utils.helpers import generate_storage_path
from foxmask.core.config import settings

class BackendType(Enum):
    """解析后端类型"""
    PIPELINE = "pipeline"
    VLM_TRANSFORMERS = "vlm-transformers"
    VLM_VLLM_ENGINE = "vlm-vllm-engine"
    VLM_HTTP_CLIENT = "vlm-http-client"


class ParseMethod(Enum):
    """解析方法"""
    AUTO = "auto"
    TXT = "txt"
    OCR = "ocr"


class MineruParser:
    """Mineru PDF解析器"""
    
    def __init__(
        self,
        output_dir: str,
        lang: str = "ch",
        backend: BackendType = BackendType.PIPELINE,
        method: ParseMethod = ParseMethod.AUTO,
        server_url: Optional[str] = None,
        formula_enable: bool = True,
        table_enable: bool = True,
        start_page_id: int = 0,
        end_page_id: Optional[int] = None
    ):
        """
        初始化解析器
        
        Args:
            output_dir: 输出目录
            lang: 语言选项，默认'ch'
            backend: 解析后端，默认pipeline
            method: 解析方法，默认auto
            server_url: VLM后端服务器URL
            formula_enable: 是否启用公式解析
            table_enable: 是否启用表格解析
            start_page_id: 起始页码
            end_page_id: 结束页码
        """
        self.output_dir = output_dir
        self.lang = lang
        self.backend = backend
        self.method = method
        self.server_url = server_url
        self.formula_enable = formula_enable
        self.table_enable = table_enable
        self.start_page_id = start_page_id
        self.end_page_id = end_page_id
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        解析单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            解析结果字典，包含中间JSON和MD内容等信息
        """
        return self.parse_pdfs([pdf_path])[0]
    
    def parse_pdfs(self, pdf_paths: List[str]) -> List[Dict[str, Any]]:
        """
        解析多个PDF文件
        
        Args:
            pdf_paths: PDF文件路径列表
            
        Returns:
            解析结果列表，每个元素包含中间JSON和MD内容等信息
        """
        path_list = [Path(path) for path in pdf_paths]
        
        # 准备文件数据
        file_name_list = []
        pdf_bytes_list = []
        lang_list = []
        
        for path in path_list:
            file_name = str(Path(path).stem)
            pdf_bytes = read_fn(path)
            file_name_list.append(file_name)
            pdf_bytes_list.append(pdf_bytes)
            lang_list.append(self.lang)
        
        # 调用内部解析方法
        results = self._do_parse(
            output_dir=self.output_dir,
            pdf_file_names=file_name_list,
            pdf_bytes_list=pdf_bytes_list,
            p_lang_list=lang_list,
            backend=self.backend.value,
            parse_method=self.method.value,
            formula_enable=self.formula_enable,
            table_enable=self.table_enable,
            server_url=self.server_url,
            start_page_id=self.start_page_id,
            end_page_id=self.end_page_id
        )
        
        return results
    
    def _do_parse(
        self,
        output_dir: str,
        pdf_file_names: List[str],
        pdf_bytes_list: List[bytes],
        p_lang_list: List[str],
        backend: str = "pipeline",
        parse_method: str = "auto",
        formula_enable: bool = True,
        table_enable: bool = True,
        server_url: Optional[str] = None,
        f_draw_layout_bbox: bool = True,
        f_draw_span_bbox: bool = True,
        f_dump_md: bool = True,
        f_dump_middle_json: bool = True,
        f_dump_model_output: bool = True,
        f_dump_orig_pdf: bool = True,
        f_dump_content_list: bool = True,
        f_make_md_mode: MakeMode = MakeMode.MM_MD,
        start_page_id: int = 0,
        end_page_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        执行解析的核心方法
        
        Returns:
            解析结果列表
        """
        results = []
        
        if backend == "pipeline":
            # 预处理PDF字节
            for idx, pdf_bytes in enumerate(pdf_bytes_list):
                new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
                pdf_bytes_list[idx] = new_pdf_bytes

            # 使用pipeline后端分析
            infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(
                pdf_bytes_list, p_lang_list, parse_method=parse_method, 
                formula_enable=formula_enable, table_enable=table_enable
            )
           

            for idx, model_list in enumerate(infer_results):
                pdf_file_name = pdf_file_names[idx]
                local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
                image_writer = FileBasedDataWriter(local_image_dir)
                
                images_list = all_image_lists[idx]
                pdf_doc = all_pdf_docs[idx]
                _lang = lang_list[idx]
                _ocr_enable = ocr_enabled_list[idx]
                
                # 转换为中间JSON格式
                middle_json = pipeline_result_to_middle_json(
                    model_list, images_list, pdf_doc, image_writer, _lang, 
                    _ocr_enable, formula_enable
                )

                #  pdf_info = middle_json["pdf_info"]
                # pdf_bytes = pdf_bytes_list[idx]
                results.append(middle_json)
                bucket_name = settings.MINIO_BUCKET_PUBLIC
                object_name = generate_storage_path(
                    access="public",
                    base_path="file",
                    tenant_id="foxmask",
                    file_name=local_image_dir)
                try:
                    minio_client.upload_directory(bucket_name,object_name)
                except Exception as e:
                    pass    
                
            
            print(local_image_dir)
           
                
        else:
            # 使用VLM后端
            if backend.startswith("vlm-"):
                backend = backend[4:]
            
            f_draw_span_bbox = False
            parse_method = "vlm"
            
            for idx, pdf_bytes in enumerate(pdf_bytes_list):
                pdf_file_name = pdf_file_names[idx]
                pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
                local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
                image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
                
                # VLM分析
                middle_json, infer_result = vlm_doc_analyze(
                    pdf_bytes, image_writer=image_writer, backend=backend, server_url=server_url
                )

                # pdf_info = middle_json["pdf_info"]
                
                results.append(middle_json)
        
        return results
    
    def _process_output(
        self,
        pdf_info: Dict[str, Any],
        pdf_file_name: str,
        local_md_dir: str,
        local_image_dir: str,
        md_writer: FileBasedDataWriter,
        f_dump_md: bool,
        f_make_md_mode: MakeMode,
        middle_json: Dict[str, Any],
        model_output: Optional[Dict[str, Any]] = None,
        is_pipeline: bool = True
    ) -> Dict[str, Any]:
        """处理输出文件并返回结果"""
        
        result = {
            "pdf_info": pdf_info,
            "middle_json": middle_json,
            "model_output": model_output,
            "md_content": None,
            "content_list": None,
            "output_dir": local_md_dir
        }
        
        image_dir = str(os.path.basename(local_image_dir))

        # 生成MD内容
        if f_dump_md:
            make_func = pipeline_union_make if is_pipeline else vlm_union_make
            md_content_str = make_func(pdf_info, f_make_md_mode, image_dir)
            result["md_content"] = md_content_str
            
            md_writer.write_string(
                f"{pdf_file_name}.md",
                md_content_str,
            )

        logger.info(f"local output dir is {local_md_dir}")
        
        return result

    
    def extract_json_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        提取PDF信息为JSON格式
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            PDF信息JSON
        """
        result = self.parse_pdf(pdf_path)
        return result
    
    def json_to_markdown (self,pdf_info:List[Dict[str,Any]],local_image_dir:str="/tmp/image") -> str:
        is_pipeline = True
        f_make_md_mode = MakeMode.MM_MD
        image_dir = str(os.path.basename(local_image_dir))
        
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        md_content_str = make_func(pdf_info, f_make_md_mode, image_dir)
        return md_content_str
    
    def json_to_text (self,pdf_info:List[Dict[str,Any]],local_image_dir:str="/tmp/image") -> str:
        is_pipeline = True
        f_make_md_mode = MakeMode.MM_MD
        image_dir = str(os.path.basename(local_image_dir))
        
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir)
        return content_list
    
        
    def convert_to_markdown(self, pdf_path: str) -> str:
        """
        将PDF转换为Markdown格式
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Markdown格式内容
        """

        result = self.parse_pdf(pdf_path)
        return result["md_content"]

    def batch_process(self, pdf_directory: str) -> List[Dict[str, Any]]:
        """
        批量处理目录下的所有PDF文件
        
        Args:
            pdf_directory: PDF文件目录
            
        Returns:
            处理结果列表
        """
        pdf_suffixes = ["pdf"]
        image_suffixes = ["png", "jpeg", "jp2", "webp", "gif", "bmp", "jpg"]

        doc_path_list = []
        for doc_path in Path(pdf_directory).glob('*'):
            if guess_suffix_by_path(doc_path) in pdf_suffixes + image_suffixes:
                doc_path_list.append(doc_path)

        return self.parse_pdfs([str(path) for path in doc_path_list])
 

# 使用示例
if __name__ == '__main__':
    # 设置环境变量（如果需要）
    # os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    
    # 创建解析器实例
    parser = MineruParser(
        output_dir="./output",
        lang="ch",
        backend=BackendType.PIPELINE,
        method=ParseMethod.AUTO
    )
    
    # 解析单个PDF
    pdf_path = "/Users/luoqi/Downloads/math-test-new-10-15.pdf"
    
    # 提取JSON信息
    json_info = parser.extract_json_info(pdf_path)
    print("JSON信息提取完成")
    print(json_info)
    # 转换为Markdown
    #md_content = parser.convert_to_markdown(pdf_path)
    #print("Markdown转换完成")
    
    # 批量处理目录
    #results = parser.batch_process("./pdfs")
    #print(f"批量处理完成，共处理 {len(results)} 个文件")