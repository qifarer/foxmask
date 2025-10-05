from abc import ABC, abstractmethod
from typing import List, Optional
from foxmask.file.dtos.upload import *
class IUploadTaskService(ABC):
    """上传任务服务接口"""
    
    @abstractmethod
    async def initialize_upload(self, input_dto: InitializeUploadInputDTO) -> InitializeUploadResponseDTO:
        pass
    
    @abstractmethod
    async def upload_chunk(self, input_dto: UploadChunkInputDTO) -> UploadChunkResponseDTO:
        pass
    
    @abstractmethod
    async def complete_upload(self, input_dto: CompleteUploadInputDTO) -> CompleteUploadResponseDTO:
        pass
    
    @abstractmethod
    async def resume_upload(self, input_dto: ResumeUploadInputDTO) -> ResumeUploadResponseDTO:
        pass
    
    @abstractmethod
    async def get_upload_task(self, task_id: str, tenant_id: str) -> GetUploadTaskResponseDTO:
        pass
    
    @abstractmethod
    async def list_upload_tasks(
        self, 
        query_dto: UploadTaskQueryDTO, 
        pagination: PaginationParams
    ) -> ListUploadTasksResponseDTO:
        pass
    
    @abstractmethod
    async def list_upload_tasks_paginated(
        self, query_dto: UploadTaskQueryDTO, skip: int, limit: int
    ) -> Tuple[List[UploadTaskDTO], int]:
        pass
    async def list_upload_task_files_paginated(
        self, query_dto: UploadTaskFileQueryDTO, skip: int, limit: int
    ) -> Tuple[List[UploadTaskFileDTO], int]:
        pass
    async def list_upload_task_file_chunks_paginated(
        self, query_dto: UploadTaskFileChunkQueryDTO, skip: int, limit: int
    ) -> Tuple[List[UploadTaskFileChunkDTO], int]:
        pass