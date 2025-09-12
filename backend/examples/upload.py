"""
Example client for chunked file upload
"""
import aiohttp
import asyncio
import hashlib
import os
from typing import Dict, Any
import json

class ChunkedUploadClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def init_upload(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize multipart upload"""
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        # 根据schema订正初始化数据
        init_data = {
            "filename": filename,
            "file_size": file_size,
            "content_type": metadata.get("content_type", "application/octet-stream"),
            "chunk_size": metadata.get("chunk_size", 5 * 1024 * 1024),
            "description": metadata.get("description"),
            "tags": metadata.get("tags", []),
            "visibility": metadata.get("visibility", "private").lower(),  # ✅ 统一转小写
            "allowed_users": metadata.get("allowed_users", []),
            "allowed_roles": metadata.get("allowed_roles", [])
        }
        
        # 移除None值
        init_data = {k: v for k, v in init_data.items() if v is not None}
        print(f"{self.base_url}/files/upload/init")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/files/upload/init",
                json=init_data,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Init failed: {await response.text()}")
                return await response.json()
    
    async def upload_chunk(self, file_path: str, chunk_number: int, 
                      upload_info: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a single chunk"""
        print(f"Uploading chunk {chunk_number}/{upload_info['total_chunks']}")
        
        chunk_size = upload_info["chunk_size"]
        file_size = os.path.getsize(file_path)
        
        # Calculate chunk boundaries
        start_byte = (chunk_number - 1) * chunk_size
        end_byte = min(chunk_number * chunk_size, file_size)
        chunk_size_bytes = end_byte - start_byte
        
        # 检查块大小是否为0（最后一个块可能为空）
        if chunk_size_bytes == 0:
            print(f"Chunk {chunk_number} has zero size, skipping")
            return {"skipped": True, "chunk_number": chunk_number}
        
        # Read chunk data
        with open(file_path, "rb") as f:
            f.seek(start_byte)
            chunk_data = f.read(chunk_size_bytes)
        
        # Calculate checksums
        checksum_md5 = hashlib.md5(chunk_data).hexdigest()
        checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()
        
        # 创建元数据 - 确保数据类型正确
        metadata = {
            "file_id": str(upload_info["file_id"]),  # 确保是字符串
            "upload_id": str(upload_info["upload_id"]),  # 确保是字符串
            "chunk_number": int(chunk_number),  # 确保是整数
            "chunk_size": int(chunk_size_bytes),  # 确保是整数
            "checksum_md5": checksum_md5,
            "checksum_sha256": checksum_sha256
        }
        
        # 验证块号是否 >= 1
        if chunk_number < 1:
            raise ValueError(f"Chunk number must be >= 1, got {chunk_number}")
        
        # 验证块大小是否 >= 0
        if chunk_size_bytes < 0:
            raise ValueError(f"Chunk size must be >= 0, got {chunk_size_bytes}")
        
        # 创建multipart表单数据
        form_data = aiohttp.FormData()
        form_data.add_field("data", json.dumps(metadata), content_type="application/json")
        form_data.add_field("file", chunk_data, filename=f"chunk-{chunk_number}", content_type="application/octet-stream")
        print("form_data:", str(form_data))
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/files/upload/chunk",
                data=form_data,
                headers={"Authorization": f"Bearer {self.token}"}
            ) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    # 记录详细的错误信息
                    print(f"Upload failed: status={response.status}, response={response_text}")
                    raise Exception(f"Chunk upload failed: {response_text}")
                
                return await response.json()
    
    async def complete_upload(self, upload_info: Dict[str, Any], 
                            chunk_etags: Dict[int, str]) -> Dict[str, Any]:
        """Complete the upload"""
        # 根据schema订正完成数据
        complete_data = {
            "file_id": upload_info["file_id"],
            "upload_id": upload_info["upload_id"],
            "chunk_etags": chunk_etags,
            "checksum_md5": upload_info.get("complete_md5"),
            "checksum_sha256": upload_info.get("complete_sha256")
        }
        
        # 移除None值
        complete_data = {k: v for k, v in complete_data.items() if v is not None}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/files/upload/complete",
                json=complete_data,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Complete failed: {await response.text()}")
                return await response.json()
    
    async def upload_file(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete file upload with progress tracking"""
        if metadata is None:
            metadata = {}
        
        # 计算完整文件的校验和（可选）
        # 这可能需要一些时间，对于大文件可以考虑跳过
        complete_md5 = None
        complete_sha256 = None
        if metadata.get("calculate_full_checksum", False):
            print("Calculating full file checksum...")
            with open(file_path, "rb") as f:
                file_data = f.read()
                complete_md5 = hashlib.md5(file_data).hexdigest()
                complete_sha256 = hashlib.sha256(file_data).hexdigest()
        
        # Initialize upload
        print("STEP-1:Initialize upload" )
        upload_info = await self.init_upload(file_path, metadata)
        total_chunks = upload_info["total_chunks"]
        
        # 添加完整校验和信息到upload_info
        upload_info["complete_md5"] = complete_md5
        upload_info["complete_sha256"] = complete_sha256
        
        # Upload all chunks
        print("STEP-2:Upload all chunks" )
        chunk_etags = {}
        for chunk_number in range(1, total_chunks + 1):
            result = await self.upload_chunk(file_path, chunk_number, upload_info)
            chunk_etags[chunk_number] = result["etag"]
            
            # Print progress
            progress = (chunk_number / total_chunks) * 100
            print(f"Upload progress: {progress:.1f}% ({chunk_number}/{total_chunks})")
        print("STEP-3:Complete upload" )
        # Complete upload
        result = await self.complete_upload(upload_info, chunk_etags)
        print(f"Upload completed: {result['filename']}")
        return result

# Usage example
async def main():
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlcnRfaDM3ZXlwIiwidHlwIjoiSldUIn0.eyJvd25lciI6ImFkbWluIiwibmFtZSI6ImZveG1hc2siLCJjcmVhdGVkVGltZSI6IiIsInVwZGF0ZWRUaW1lIjoiIiwiZGVsZXRlZFRpbWUiOiIiLCJpZCI6ImFkbWluL2ZveG1hc2siLCJ0eXBlIjoiYXBwbGljYXRpb24iLCJwYXNzd29yZCI6IiIsInBhc3N3b3JkU2FsdCI6IiIsInBhc3N3b3JkVHlwZSI6IiIsImRpc3BsYXlOYW1lIjoiIiwiZmlyc3ROYW1lIjoiIiwibGFzdE5hbWUiOiIiLCJhdmF0YXIiOiIiLCJhdmF0YXJUeXBlIjoiIiwicGVybWFuZW50QXZhdGFyIjoiIiwiZW1haWwiOiIiLCJlbWFpbFZlcmlmaWVkIjpmYWxzZSwicGhvbmUiOiIiLCJjb3VudHJ5Q29kZSI6IiIsInJlZ2lvbiI6IiIsImxvY2F0aW9uIjoiIiwiYWRkcmVzcyI6W10sImFmZmlsaWF0aW9uIjoiIiwidGl0bGUiOiIiLCJpZENhcmRUeXBlIjoiIiwiaWRDYXJkIjoiIiwiaG9tZXBhZ2UiOiIiLCJiaW8iOiIiLCJsYW5ndWFnZSI6IiIsImdlbmRlciI6IiIsImJpcnRoZGF5IjoiIiwiZWR1Y2F0aW9uIjoiIiwic2NvcmUiOjAsImthcm1hIjowLCJyYW5raW5nIjowLCJpc0RlZmF1bHRBdmF0YXIiOmZhbHNlLCJpc09ubGluZSI6ZmFsc2UsImlzQWRtaW4iOmZhbHNlLCJpc0ZvcmJpZGRlbiI6ZmFsc2UsImlzRGVsZXRlZCI6ZmFsc2UsInNpZ251cEFwcGxpY2F0aW9uIjoiIiwiaGFzaCI6IiIsInByZUhhc2giOiIiLCJhY2Nlc3NLZXkiOiIiLCJhY2Nlc3NTZWNyZXQiOiIiLCJnaXRodWIiOiIiLCJnb29nbGUiOiIiLCJxcSI6IiIsIndlY2hhdCI6IiIsImZhY2Vib29rIjoiIiwiZGluZ3RhbGsiOiIiLCJ3ZWlibyI6IiIsImdpdGVlIjoiIiwibGlua2VkaW4iOiIiLCJ3ZWNvbSI6IiIsImxhcmsiOiIiLCJnaXRsYWIiOiIiLCJjcmVhdGVkSXAiOiIiLCJsYXN0U2lnbmluVGltZSI6IiIsImxhc3RTaWduaW5JcCI6IiIsInByZWZlcnJlZE1mYVR5cGUiOiIiLCJyZWNvdmVyeUNvZGVzIjpudWxsLCJ0b3RwU2VjcmV0IjoiIiwibWZhUGhvbmVFbmFibGVkIjpmYWxzZSwibWZhRW1haWxFbmFibGVkIjpmYWxzZSwibGRhcCI6IiIsInByb3BlcnRpZXMiOnt9LCJyb2xlcyI6W10sInBlcm1pc3Npb25zIjpbXSwiZ3JvdXBzIjpbXSwibGFzdFNpZ25pbldyb25nVGltZSI6IiIsInNpZ25pbldyb25nVGltZXMiOjAsIm1hbmFnZWRBY2NvdW50cyI6bnVsbCwidG9rZW5UeXBlIjoiYWNjZXNzLXRva2VuIiwidGFnIjoiIiwiYXpwIjoiMjVjN2JiZTJmZWVkM2YzNzhkMjEiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwMDAiLCJzdWIiOiJhZG1pbi9mb3htYXNrIiwiYXVkIjpbIjI1YzdiYmUyZmVlZDNmMzc4ZDIxIl0sImV4cCI6MTc1ODIyNDA4OSwibmJmIjoxNzU3NjE5Mjg5LCJpYXQiOjE3NTc2MTkyODksImp0aSI6ImFkbWluL2JiNjY3MDc2LTYzMmItNDRjYS05NDgxLTMzNjk1MDZjYWViNCJ9.C1UVJkluWDf1RIm_cJYJmYD1qsk2vFrF0jiblLwCQuEbmH-i1qCqnI2-9uL7AWBny-Jk8kQrr-376dhQbPF3-huA5M4GctWxQ-sqHHRmMaF6i3zQWOTkWhJMkouLCLcIae8LHlT4lZ6wqUBumBq-fmGi5NhvBxd883ZOa2RW7GC6YlpdwiAIYSwbWCCxqO3JZZKctY84o1mmZAIcwe9xuhtSqfRJ6xt5ttKKNhZMXa8iqdftm4ALdKsm1STX6KxcQF3MCbZIAeih_-iGq0yqHakzn1uuLwEq4qKgSpHE0rXOOF45LCrRFqFZ3xjHbsZAATz9VuLKxUBspN-pTtEfgcElMOI1CUFXLYxhzZgKsT8pRjN70lNlIh5kfGcvaOOB5vxNQ_HxK2ZlxH2KgjCzHrGva0KOI1Vj6m_fMPGHhYxg0D6KbBbHZihhg1kSqlNq7zrY5uLVp_vPM4aJc0cnpJ0vB3817N06bkza0NOIS0mN2nNmB8aR8lQDCHlKS_KlHx2LMW_Q7oxNSiQoXjWNqxEFY3LaegRqBPEILNaVP4F64Wv7jNPbfTuiLGItlmOeHvOZu_tkrC7tmO0QMN96sVonGDPAHvNzLVHDl2iUkV2JKrBsfb8SB-UyM8eMMiitbx5iUS9Z-VkUS6jn5_o9SKIZQ1xcWFtfqE0X64qx3bY" 
    client = ChunkedUploadClient("http://localhost:8888/api/", token)
    # filename = "/Users/luoqi/Downloads/购物顾问智能体落地分析报告.md"
    # filename = "/Users/luoqi/Downloads/AI-A2A.drawio.png"
    # filename = "/Users/luoqi/Downloads/普通高中教科书·数学必修 第一册.pdf"
    filename = "/Users/luoqi/Downloads/sp_salebill_21.sql"
    
    try:
        result = await client.upload_file(
            filename,
            {
                "description": "Large file upload example",
                "tags": ["example", "large-file"],
                "visibility": "PRIVATE",  # 根据FileVisibility枚举添加
                "content_type": "application/pdf",  # 指定正确的content_type
                "calculate_full_checksum": True  # 可选：计算完整文件校验和
            }
        )
        print(f"File uploaded successfully: {result}")
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

