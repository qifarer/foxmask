# 使用服务端的GraphQL API调用
import requests
import json

# GraphQL端点
GRAPHQL_URL = "http://localhost:8000/graphql"

def execute_graphql(query: str, variables: dict = None, token: str = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
    return response.json()

# 创建上传任务
create_task_query = """
mutation CreateUploadTask($input: UploadTaskCreateInput!) {
  createUploadTask(input: $input) {
    success
    message
    data {
      id
      title
      taskStatus
      totalFiles
      totalSize
    }
  }
}
"""

variables = {
    "input": {
        "taskType": "BATCH_UPLOAD",
        "sourceType": "SINGLE_DIRECTORY", 
        "sourcePaths": ["/path/to/upload/directory"],
        "title": "项目文档上传",
        "uploadStrategy": "PARALLEL",
        "preserveStructure": True,
        "baseUploadPath": "projects/2024"
    }
}

result = execute_graphql(create_task_query, variables, "your-jwt-token")
print(json.dumps(result, indent=2))