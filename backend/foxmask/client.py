# -*- coding: utf-8 -*-
# foxmask/file/graphql_client.py
# Copyright (C) 2024 FoxMask Inc.
# author: Roky
# GraphQL client for chunked file upload

import aiohttp
import asyncio
import hashlib
import os
from typing import Dict, Any, Optional
import json
import base64
from pathlib import Path
from foxmask.core.kafka import kafka_manager

class GraphQLChunkedUploadClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    async def _execute_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query or mutation"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/graphql",
                json=payload,
                headers=self.headers
            ) as response:
                response_text = await response.text()
                print(f"GraphQL response status: {response.status}")
                
                if response.status != 200:
                    raise Exception(f"GraphQL request failed: {response_text}")
                
                try:
                    result = await response.json()
                except json.JSONDecodeError:
                    raise Exception(f"Invalid JSON response: {response_text}")
                
                if "errors" in result:
                    error_messages = [error.get('message', 'Unknown error') for error in result['errors']]
                    raise Exception(f"GraphQL errors: {error_messages}")
                
                return result.get("data", {})

    async def init_upload(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize multipart upload"""
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        # Prepare input data according to FileCreateInput schema (using camelCase for GraphQL)
        init_data = {
            "filename": filename,
            "fileSize": file_size,  # camelCase for GraphQL
            "contentType": metadata.get("content_type", "application/octet-stream"),  # camelCase
            "chunkSize": metadata.get("chunk_size", 5 * 1024 * 1024),  # camelCase
            "description": metadata.get("description"),
            "tags": metadata.get("tags", []),
            "visibility": metadata.get("visibility", "PRIVATE"),
            "allowedUsers": metadata.get("allowed_users", []),  # camelCase
            "allowedRoles": metadata.get("allowed_roles", []),  # camelCase
            "metadata": metadata.get("metadata", {}),
            "isMultipart": True  # camelCase
        }

        # Remove None values
        init_data = {k: v for k, v in init_data.items() if v is not None}

        query = """
        mutation InitUpload($fileData: FileCreateInput!) {
            initUpload(fileData: $fileData) {
                success
                message
                result {
                    fileId
                    uploadId
                    chunkSize
                    totalChunks
                    chunkUrls
                    minioBucket
                }
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {
            "fileData": init_data
        }

        print(f"Initializing upload for {filename}")
        result = await self._execute_graphql(query, variables)
        print(f"Init upload result: {result}")
        upload_result = result.get("initUpload", {})
        
        if not upload_result.get("success"):
            error = upload_result.get("error", {})
            raise Exception(f"Failed to initialize upload: {error.get('message', 'Unknown error')}")
        
        return upload_result["result"]

    async def upload_chunk(self, file_path: str, chunk_number: int, upload_info: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a single chunk"""
        print(f"Uploading chunk {chunk_number}/{upload_info['totalChunks']}")

        chunk_size = upload_info["chunkSize"]
        file_size = os.path.getsize(file_path)

        # Calculate chunk boundaries
        start_byte = (chunk_number - 1) * chunk_size
        end_byte = min(chunk_number * chunk_size, file_size)
        chunk_size_bytes = end_byte - start_byte

        # Skip empty chunks
        if chunk_size_bytes == 0:
            print(f"Chunk {chunk_number} has zero size, skipping")
            return {"skipped": True, "chunkNumber": chunk_number}

        # Read chunk data
        with open(file_path, "rb") as f:
            f.seek(start_byte)
            chunk_data = f.read(chunk_size_bytes)

        # Calculate checksums
        checksum_md5 = hashlib.md5(chunk_data).hexdigest()
        checksum_sha256 = hashlib.sha256(chunk_data).hexdigest()

        # Encode chunk data as base64
        chunk_data_b64 = base64.b64encode(chunk_data).decode("utf-8")

        # Prepare chunk upload input (using camelCase for GraphQL)
        chunk_input = {
            "fileId": upload_info["fileId"],
            "uploadId": upload_info["uploadId"],
            "chunkNumber": chunk_number,
            "chunkSize": chunk_size_bytes,
            "checksumMd5": checksum_md5,  # camelCase
            "checksumSha256": checksum_sha256,  # camelCase
            "chunkData": chunk_data_b64  # camelCase
        }

        query = """
        mutation UploadChunk($chunkData: ChunkUploadInput!) {
            uploadChunk(chunkData: $chunkData) {
                success
                message
                result {
                    fileId
                    uploadId
                    chunkNumber
                    minioEtag
                    status
                }
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {"chunkData": chunk_input}

        result = await self._execute_graphql(query, variables)
        chunk_result = result.get("uploadChunk", {})
        
        if not chunk_result.get("success"):
            error = chunk_result.get("error", {})
            raise Exception(f"Failed to upload chunk {chunk_number}: {error.get('message', 'Unknown error')}")
        
        return chunk_result["result"]

    async def complete_upload(self, upload_info: Dict[str, Any], chunk_etags: Dict[int, str]) -> Dict[str, Any]:
        """Complete the upload"""
        # Prepare chunk etags as a list of ChunkEtagInput (using camelCase)
        chunk_etags_input = [{"chunkNumber": k, "etag": v} for k, v in chunk_etags.items()]

        complete_input = {
            "fileId": upload_info["fileId"],
            "uploadId": upload_info["uploadId"],
            "chunkEtags": chunk_etags_input,  # camelCase
            "checksumMd5": upload_info.get("completeMd5"),  # camelCase
            "checksumSha256": upload_info.get("completeSha256")  # camelCase
        }

        # Remove None values
        complete_input = {k: v for k, v in complete_input.items() if v is not None}

        query = """
        mutation CompleteUpload($completeData: CompleteUploadInput!) {
            completeUpload(completeData: $completeData) {
                success
                message
                file {
                    id
                    filename
                    status
                    fileSize
                    contentType
                    description
                    tags
                    visibility
                    uploadedAt
                }
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {"completeData": complete_input}

        print(f"Completing upload for file ID {upload_info['fileId']}")
        result = await self._execute_graphql(query, variables)
        complete_result = result.get("completeUpload", {})
        
        if not complete_result.get("success"):
            error = complete_result.get("error", {})
            raise Exception(f"Failed to complete upload: {error.get('message', 'Unknown error')}")
        
        return complete_result["file"]

    async def get_upload_progress(self, file_id: str) -> Dict[str, Any]:
        """Get upload progress"""
        query = """
        query GetUploadProgress($fileId: ID!) {
            uploadProgress(fileId: $fileId) {
                success
                message
                progress {
                    fileId
                    filename
                    status
                    uploadedChunks
                    totalChunks
                    progressPercentage
                }
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {"fileId": file_id}

        result = await self._execute_graphql(query, variables)
        progress_result = result.get("uploadProgress", {})
        
        if not progress_result.get("success"):
            error = progress_result.get("error", {})
            raise Exception(f"Failed to get upload progress: {error.get('message', 'Unknown error')}")
        
        return progress_result["progress"]

    async def upload_file(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete file upload with progress tracking"""
        if metadata is None:
            metadata = {}

        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Calculate full file checksums
        print("Calculating full file checksum...")
        complete_md5 = None
        complete_sha256 = None
        
        # Use chunked reading for large files
        chunk_size = 1024 * 1024  # 1MB chunks for checksum calculation
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
        
        complete_md5 = md5_hash.hexdigest()
        complete_sha256 = sha256_hash.hexdigest()

        # Initialize upload
        print("STEP-1: Initialize upload")
        upload_info = await self.init_upload(file_path, metadata)
        total_chunks = upload_info["totalChunks"]

        # Add checksums to upload_info (using camelCase)
        upload_info["completeMd5"] = complete_md5
        upload_info["completeSha256"] = complete_sha256

        # Upload all chunks
        print("STEP-2: Upload all chunks")
        chunk_etags = {}
        
        for chunk_number in range(1, total_chunks + 1):
            try:
                result = await self.upload_chunk(file_path, chunk_number, upload_info)
                if not result.get("skipped"):
                    chunk_etags[chunk_number] = result["minioEtag"]
                
                # Print progress
                progress = (chunk_number / total_chunks) * 100
                print(f"Upload progress: {progress:.1f}% ({chunk_number}/{total_chunks})")
                
                # Check progress periodically
                if chunk_number % 10 == 0 or chunk_number == total_chunks:
                    progress_info = await self.get_upload_progress(upload_info["fileId"])
                    print(f"Current status: {progress_info['status']}, Uploaded: {progress_info['uploadedChunks']}/{progress_info['totalChunks']}")
                    
            except Exception as e:
                print(f"Error uploading chunk {chunk_number}: {e}")
                # Try to resume upload
                try:
                    resume_info = await self.resume_upload(upload_info["fileId"])
                    print(f"Resumed upload, missing chunks: {resume_info.get('missingChunks', [])}")
                    # Continue from current chunk
                except Exception as resume_error:
                    print(f"Failed to resume upload: {resume_error}")
                    raise

        # Complete upload
        print("STEP-3: Complete upload")
        result = await self.complete_upload(upload_info, chunk_etags)
        print(f"Upload completed: {result['filename']} (ID: {result['id']})")
        return result

    async def resume_upload(self, file_id: str) -> Dict[str, Any]:
        """Resume interrupted upload"""
        query = """
        mutation ResumeUpload($fileId: ID!) {
            resumeUpload(fileId: $fileId) {
                success
                message
                result {
                    fileId
                    uploadId
                    missingChunks
                    chunkUrls
                }
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {"fileId": file_id}

        result = await self._execute_graphql(query, variables)
        resume_result = result.get("resumeUpload", {})
        
        if not resume_result.get("success"):
            error = resume_result.get("error", {})
            raise Exception(f"Failed to resume upload: {error.get('message', 'Unknown error')}")
        
        return resume_result["result"]

    async def abort_upload(self, file_id: str) -> bool:
        """Abort upload"""
        query = """
        mutation AbortUpload($fileId: ID!) {
            abortUpload(fileId: $fileId) {
                success
                message
                error {
                    message
                    code
                    details
                }
            }
        }
        """
        variables = {"fileId": file_id}

        result = await self._execute_graphql(query, variables)
        abort_result = result.get("abortUpload", {})
        
        if not abort_result.get("success"):
            error = abort_result.get("error", {})
            raise Exception(f"Failed to abort upload: {error.get('message', 'Unknown error')}")
        
        return True

# Usage example
async def main():
    # Replace with your actual token
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImNlcnRfaDM3ZXlwIiwidHlwIjoiSldUIn0.eyJvd25lciI6ImFkbWluIiwibmFtZSI6ImZveG1hc2siLCJjcmVhdGVkVGltZSI6IiIsInVwZGF0ZWRUaW1lIjoiIiwiZGVsZXRlZFRpbWUiOiIiLCJpZCI6ImFkbWluL2ZveG1hc2siLCJ0eXBlIjoiYXBwbGljYXRpb24iLCJwYXNzd29yZCI6IiIsInBhc3N3b3JkU2FsdCI6IiIsInBhc3N3b3JkVHlwZSI6IiIsImRpc3BsYXlOYW1lIjoiIiwiZmlyc3ROYW1lIjoiIiwibGFzdE5hbWUiOiIiLCJhdmF0YXIiOiIiLCJhdmF0YXJUeXBlIjoiIiwicGVybWFuZW50QXZhdGFyIjoiIiwiZW1haWwiOiIiLCJlbWFpbFZlcmlmaWVkIjpmYWxzZSwicGhvbmUiOiIiLCJjb3VudHJ5Q29kZSI6IiIsInJlZ2lvbiI6IiIsImxvY2F0aW9uIjoiIiwiYWRkcmVzcyI6W10sImFmZmlsaWF0aW9uIjoiIiwidGl0bGUiOiIiLCJpZENhcmRUeXBlIjoiIiwiaWRDYXJkIjoiIiwiaG9tZXBhZ2UiOiIiLCJiaW8iOiIiLCJsYW5ndWFnZSI6IiIsImdlbmRlciI6IiIsImJpcnRoZGF5IjoiIiwiZWR1Y2F0aW9uIjoiIiwic2NvcmUiOjAsImthcm1hIjowLCJyYW5raW5nIjowLCJpc0RlZmF1bHRBdmF0YXIiOmZhbHNlLCJpc09ubGluZSI6ZmFsc2UsImlzQWRtaW4iOmZhbHNlLCJpc0ZvcmJpZGRlbiI6ZmFsc2UsImlzRGVsZXRlZCI6ZmFsc2UsInNpZ251cEFwcGxpY2F0aW9uIjoiIiwiaGFzaCI6IiIsInByZUhhc2giOiIiLCJhY2Nlc3NLZXkiOiIiLCJhY2Nlc3NTZWNyZXQiOiIiLCJnaXRodWIiOiIiLCJnb29nbGUiOiIiLCJxcSI6IiIsIndlY2hhdCI6IiIsImZhY2Vib29rIjoiIiwiZGluZ3RhbGsiOiIiLCJ3ZWlibyI6IiIsImdpdGVlIjoiIiwibGlua2VkaW4iOiIiLCJ3ZWNvbSI6IiIsImxhcmsiOiIiLCJnaXRsYWIiOiIiLCJjcmVhdGVkSXAiOiIiLCJsYXN0U2lnbmluVGltZSI6IiIsImxhc3RTaWduaW5JcCI6IiIsInByZWZlcnJlZE1mYVR5cGUiOiIiLCJyZWNvdmVyeUNvZGVzIjpudWxsLCJ0b3RwU2VjcmV0IjoiIiwibWZhUGhvbmVFbmFibGVkIjpmYWxzZSwibWZhRW1haWxFbmFibGVkIjpmYWxzZSwibGRhcCI6IiIsInByb3BlcnRpZXMiOnt9LCJyb2xlcyI6W10sInBlcm1pc3Npb25zIjpbXSwiZ3JvdXBzIjpbXSwibGFzdFNpZ25pbldyb25nVGltZSI6IiIsInNpZ25pbldyb25nVGltZXMiOjAsIm1hbmFnZWRBY2NvdW50cyI6bnVsbCwidG9rZW5UeXBlIjoiYWNjZXNzLXRva2VuIiwidGFnIjoiIiwiYXpwIjoiMjVjN2JiZTJmZWVkM2YzNzhkMjEiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwMDAiLCJzdWIiOiJhZG1pbi9mb3htYXNrIiwiYXVkIjpbIjI1YzdiYmUyZmVlZDNmMzc4ZDIxIl0sImV4cCI6MTc1ODQxNzgxNiwibmJmIjoxNzU3ODEzMDE2LCJpYXQiOjE3NTc4MTMwMTYsImp0aSI6ImFkbWluLzk2YzExMGNjLTExNzItNDZiMS1hZTBlLTA3MDU0MGQ2NjFjMiJ9.HfsCWi9sqqSjPjyyV9xBB6skFzVqJzpmEjdLfy-2-BwGTkcNtM_2SciXeWfRZUiyOX_YZq9CvAog-oK8KRKnn0lJcjK_XSkX4D_DIIlBdlpcZOV6V-0XRzdsJoUX1azr-jretjhJqSiMK4uNu7wGna5ba1soabITMM0bbFq3xFbFIOVnkw3JJ4YUcaYgO4CZjj_g68Ly6iZb9iKMq6IG8VEbUZeiArMHQC6YfcYD0nNw2LBV5Wv05ohanYjq0_PU6s9U0ywk7JyGQWWW7GF0_NDhirMwkXK2e_qh_bGZ016ktltqJuFe4NwUrxjwfelAXgbhTc8gZgGB-9DizHakyFyJPVVgO83t1NUXywyHpldxcUTuFbAwZNoX3UvKvyMTgLAB98XXDKZ5CIqxu2Ko11bcla6AzijJedGbinVqU14Y5jXWtSLFTvCXarJZwTQ2VMfCvIRVQ2CmcIPObbUOSG9-xsEL69BXKnLRvMt426PK7KcKRPuxz1oMVhDUlKQYZ0YAXLsUrVfHY2E5q1egWstJfPZUJMBO5LAxX9xqoj4A3nLtBD0ulA2desQHlwiLyFrHhj-bNblKdwnAY9_wPXICh0gSn5JA5xUi-MNzoRr31dWbTRGNL1vdg6NAGYa5NqL5uKu5XZHeE3GYOSp0U-Xt6l9zV1rvnJ0EZYZjUbk"
    
    client = GraphQLChunkedUploadClient("http://localhost:8888", token)
    # Test file path
    # filename = "/Users/luoqi/Downloads/products_export_2.zip"
    # filename = "/Users/luoqi/Downloads/AI-A2A.drawio.png"
    # filename = "/Users/luoqi/Downloads/普通高中教科书·数学必修 第一册.pdf"
    # filename = "/Users/luoqi/Downloads/sp_salebill_21.sql"
    filenames = ['/Users/luoqi/Downloads/购物顾问智能体落地分析报告.pdf',
                 '/Users/luoqi/Downloads/购物顾问智能体落地分析报告.md',
                 '/Users/luoqi/Downloads/sp_salebill_21.sql',
                 '/Users/luoqi/Downloads/AI-A2A.drawio.png',
                 '/Users/luoqi/Downloads/products_export_2.zip']
    try:
        for filename in filenames:
            result = await client.upload_file(
                filename,
                {
                    "description": "Large file upload example",
                    "tags": ["example", "large-file"],
                    "visibility": "PRIVATE",
                    "content_type": "application/csv",
                    "chunk_size": 5 * 1024 * 1024,  # 5MB chunks
                    "metadata": {
                        "source": "graphql-client",
                        "category": "document"
                    }
                }
            )
            print(f"File uploaded successfully: {result}")
            print(f"KAFKA TOPICS:{str(await kafka_manager.list_topics())}")
            print(f"KAFKA PARTITIONS:{str(await kafka_manager.get_topic_info('CREATE_KNOWLEDGE_ITEM'))}"   )
    except Exception as e:
        print(f"Upload failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())