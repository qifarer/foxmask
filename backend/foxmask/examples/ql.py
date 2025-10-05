import requests
import json
from typing import Optional, Dict, Any

class FileClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.graphql_endpoint = f"{self.base_url}/graphql"
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def execute_query(self, query: str, variables: Dict[str, Any] = None):
        """执行GraphQL查询"""
        # 确保query是有效的字符串
        if not query or not isinstance(query, str):
            raise Exception("Invalid query parameter")
        
        # 构建正确的GraphQL请求格式
        payload = {
            "query": query.strip(),
            "variables": variables or {}
        }
        
        print(f"Sending request to: {self.graphql_endpoint}")
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                self.graphql_endpoint,
                headers=self.headers,
                json=payload,  # 使用json参数自动序列化
                timeout=30
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    error_msg = result["errors"][0]["message"] if result["errors"] else "Unknown GraphQL error"
                    raise Exception(f"GraphQL error: {error_msg}")
                return result
            else:
                raise Exception(f"HTTP error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    def get_files(
        self, 
        page: int = 1, 
        page_size: int = 10,
        status: Optional[str] = None,
        visibility: Optional[str] = None
    ):
        """获取文件列表（使用字符串参数）"""
        query = """
         query {
         files {
            id
            filename
            fileSize
            status
            uploadProgress
            createdAt
         
         }
            
        }
        """
        
        variables = {
            "page": page,
            "pageSize": page_size,
            "status": status,
            "visibility": visibility
        }
        

        if status is not None:
            variables["status"] = status.upper()  # 转换为大写以匹配枚举
        if visibility is not None:
            variables["visibility"] = visibility.upper()
        variables={}
        print(query)
        return self.execute_query(query, variables)


    def health_check(self):
        """健康检查"""
        query = """
       query {   health } 
        """
        return self.execute_query(query)

# 使用示例
if __name__ == "__main__":
    # 初始化客户端 - 先不带token测试
    valid_token ="eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlcnRfaDM3ZXlwIiwidHlwIjoiSldUIn0.eyJvd25lciI6ImFkbWluIiwibmFtZSI6ImZveG1hc2siLCJjcmVhdGVkVGltZSI6IiIsInVwZGF0ZWRUaW1lIjoiIiwiZGVsZXRlZFRpbWUiOiIiLCJpZCI6ImFkbWluL2ZveG1hc2siLCJ0eXBlIjoiYXBwbGljYXRpb24iLCJwYXNzd29yZCI6IiIsInBhc3N3b3JkU2FsdCI6IiIsInBhc3N3b3JkVHlwZSI6IiIsImRpc3BsYXlOYW1lIjoiIiwiZmlyc3ROYW1lIjoiIiwibGFzdE5hbWUiOiIiLCJhdmF0YXIiOiIiLCJhdmF0YXJUeXBlIjoiIiwicGVybWFuZW50QXZhdGFyIjoiIiwiZW1haWwiOiIiLCJlbWFpbFZlcmlmaWVkIjpmYWxzZSwicGhvbmUiOiIiLCJjb3VudHJ5Q29kZSI6IiIsInJlZ2lvbiI6IiIsImxvY2F0aW9uIjoiIiwiYWRkcmVzcyI6W10sImFmZmlsaWF0aW9uIjoiIiwidGl0bGUiOiIiLCJpZENhcmRUeXBlIjoiIiwiaWRDYXJkIjoiIiwiaG9tZXBhZ2UiOiIiLCJiaW8iOiIiLCJsYW5ndWFnZSI6IiIsImdlbmRlciI6IiIsImJpcnRoZGF5IjoiIiwiZWR1Y2F0aW9uIjoiIiwic2NvcmUiOjAsImthcm1hIjowLCJyYW5raW5nIjowLCJpc0RlZmF1bHRBdmF0YXIiOmZhbHNlLCJpc09ubGluZSI6ZmFsc2UsImlzQWRtaW4iOmZhbHNlLCJpc0ZvcmJpZGRlbiI6ZmFsc2UsImlzRGVsZXRlZCI6ZmFsc2UsInNpZ251cEFwcGxpY2F0aW9uIjoiIiwiaGFzaCI6IiIsInByZUhhc2giOiIiLCJhY2Nlc3NLZXkiOiIiLCJhY2Nlc3NTZWNyZXQiOiIiLCJnaXRodWIiOiIiLCJnb29nbGUiOiIiLCJxcSI6IiIsIndlY2hhdCI6IiIsImZhY2Vib29rIjoiIiwiZGluZ3RhbGsiOiIiLCJ3ZWlibyI6IiIsImdpdGVlIjoiIiwibGlua2VkaW4iOiIiLCJ3ZWNvbSI6IiIsImxhcmsiOiIiLCJnaXRsYWIiOiIiLCJjcmVhdGVkSXAiOiIiLCJsYXN0U2lnbmluVGltZSI6IiIsImxhc3RTaWduaW5JcCI6IiIsInByZWZlcnJlZE1mYVR5cGUiOiIiLCJyZWNvdmVyeUNvZGVzIjpudWxsLCJ0b3RwU2VjcmV0IjoiIiwibWZhUGhvbmVFbmFibGVkIjpmYWxzZSwibWZhRW1haWxFbmFibGVkIjpmYWxzZSwibGRhcCI6IiIsInByb3BlcnRpZXMiOnt9LCJyb2xlcyI6W10sInBlcm1pc3Npb25zIjpbXSwiZ3JvdXBzIjpbXSwibGFzdFNpZ25pbldyb25nVGltZSI6IiIsInNpZ25pbldyb25nVGltZXMiOjAsIm1hbmFnZWRBY2NvdW50cyI6bnVsbCwidG9rZW5UeXBlIjoiYWNjZXNzLXRva2VuIiwidGFnIjoiIiwiYXpwIjoiMjVjN2JiZTJmZWVkM2YzNzhkMjEiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwMDAiLCJzdWIiOiJhZG1pbi9mb3htYXNrIiwiYXVkIjpbIjI1YzdiYmUyZmVlZDNmMzc4ZDIxIl0sImV4cCI6MTc1ODM3NDc0NSwibmJmIjoxNzU3NzY5OTQ1LCJpYXQiOjE3NTc3Njk5NDUsImp0aSI6ImFkbWluL2FkMjE1NzE5LWEyMDEtNDVhNi04N2NkLWRiNzA3NTQxMDJkYSJ9.OKAXc8w-3IHNUmSjW57bYZNGZw1m7vAs12HgLv3lcaT4Zmzq43Ac79T3xv1CIuQOcd1OHP9SQ25Ok0_M4jTJC8Sa1l3JD_gmCN-lhlJH88HFjNJA5fS1dmSzIMKKRUE54Mizd9R7xHltI4HSdS6H3touqNXHBBX1yK29jtZqgSii1filcflwa7RLiRVBo040nj0WibmQCjNi7XXyZf3qxpT0alSBGDqsGfv-JCvL0rTvMIa0HSdy5e4QzcFRO2sbP5Gk6oh7ZTIuhRf1fPi4c5Yc9anX9RbIh4xTh9EQ3dkmz8mpgoUBZfMgRtTGZ4sa0275h3MQNnD094Y7UjChMFCeheDLXBbW0JPSy0BCYPA-JEUQPn0cWNLsVebtnE3K83G5zFWMTVcN2zkgDUnP-VzFTHxS1YbNZ4qKMELDGPItPgLVyK4AOrum6LB0TTiXpyq0wshnpjP6CZidfglGyncxmxt4QZFnAKMfQv9fkyT_eDY1q4i65iSf3oxSxjd9hMpoQaUlUwP2QcyDdGb7fzY9FWed8hLq0yNS2QFyUO2is9nLRzT7ERmu3HIzgxw1Iaq2cEVdB3i4cGkHWD2h_zkS5Zp5qS59xsWBTjncquND2rrww__3NmNlaYuWDGITG2K26-wI5bWHznGsvFo7LuqcRYGprJi2K8Zv5-MBjIE"
   
    client = FileClient("http://localhost:8888",token=valid_token)
    
    try:
        print("Testing health check...")
        health_result = client.health_check()
        print("Health check successful:", health_result)
        
        print("Testing files query...")
        files_result = client.get_files(page=1, page_size=5, status="COMPLETED", visibility="PUBLIC")
        print("Files query successful:", json.dumps(files_result, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")

