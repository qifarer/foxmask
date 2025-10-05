import strawberry
from typing import Optional, List, AsyncGenerator
from typing_extensions import Annotated
from strawberry.relay import Node, Connection, PageInfo as RelayPageInfo
from strawberry.scalars import JSON
from datetime import datetime
import asyncio
from .enums import FileTypeGql, UploadProcStatusGql, UploadTaskTypeGql, UploadSourceTypeGql, UploadStrategyGql
from foxmask.core.schema import (
    VisibilityEnum,
    StatusEnum,
    BaseResponse,
    BaseInput,
    BaseEdge,
    BaseConnection,
    PageInfo,
    Error,  # Assuming Error is defined as @strawberry.type class Error: message: str, code: str, field: Optional[str] = None
)

# Entity types with relationships
@strawberry.type
class UploadTaskFileChunk(Node):
    uid: str
    tenant_id: str
    master_id: str
    note: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    proc_status: UploadProcStatusGql
    file_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    minio_etag: Optional[str]
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    retry_count: int
    max_retries: int

@strawberry.type
class UploadTaskFile(Node):
    uid: str
    tenant_id: str
    master_id: str
    note: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    proc_status: UploadProcStatusGql
    original_path: str
    storage_path: str
    filename: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    checksum_md5: Optional[str]
    checksum_sha256: Optional[str]
    total_chunks: int
    uploaded_chunks: int
    current_chunk: int
    progress: float
    upload_speed: Optional[float]
    estimated_time_remaining: Optional[float]
    extracted_metadata: Optional[JSON]
    upload_started_at: Optional[datetime]
    upload_completed_at: Optional[datetime]
    chunks: "UploadTaskFileChunkConnection"

UploadTaskFileChunkConnection = Annotated[
    BaseConnection[UploadTaskFileChunk],
    strawberry.relay.connection(name="UploadTaskFileChunkConnection")
]

@strawberry.type
class UploadTask(Node):
    uid: str
    tenant_id: str 
    title: str 
    desc: Optional[str] 
    category: Optional[str] 
    tags: Optional[List[str]] 
    note: Optional[str] 
    status: StatusEnum
    visibility: VisibilityEnum 
    created_at: datetime 
    updated_at: datetime 
    archived_at: Optional[datetime] 
    created_by: Optional[str] 
    allowed_users: List[str] 
    allowed_roles: List[str] 
    proc_meta: Optional[JSON] 
    error_info: Optional[JSON] 
    metadata: Optional[JSON] 
    proc_status: UploadProcStatusGql
    source_type: UploadSourceTypeGql
    source_paths: List[str]
    upload_strategy: UploadStrategyGql
    max_parallel_uploads: int
    chunk_size: int
    preserve_structure: bool
    base_upload_path: Optional[str]
    auto_extract_metadata: bool
    file_type_filters: List[FileTypeGql]
    max_file_size: Optional[int]
    discovered_files: int
    processing_files: int
    total_files: int
    completed_files: int
    failed_files: int
    total_size: int
    uploaded_size: int
    discovery_started_at: Optional[datetime]
    discovery_completed_at: Optional[datetime]
    files: "UploadTaskFileConnection"

UploadTaskFileConnection = Annotated[
    BaseConnection[UploadTaskFile],
    strawberry.relay.connection(name="UploadTaskFileConnection")
]

UploadTaskConnection = Annotated[
    BaseConnection[UploadTask],
    strawberry.relay.connection(name="UploadTaskConnection")
]

# Input types for the scenarios
@strawberry.input
class InitializeUploadInput(BaseInput):
    tenant_id: str
    created_by: str
    title: str
    desc: Optional[str] = None
    task_type: Optional[UploadTaskTypeGql] = UploadTaskTypeGql.BATCH
    source_type: UploadSourceTypeGql
    source_paths: List[str]
    upload_strategy: UploadStrategyGql
    max_parallel_uploads: int = 1
    chunk_size: int
    preserve_structure: bool = False
    base_upload_path: Optional[str] = None
    auto_extract_metadata: bool = False
    file_type_filters: List[FileTypeGql] = strawberry.field(default_factory=list)
    max_file_size: Optional[int] = None
    files: Optional[List["InitializeUploadFileInput"]] = None
    resume_task_id: Optional[str] = None

@strawberry.input
class InitializeUploadFileInput(BaseInput):
    original_path: str
    filename: str
    file_size: int
    file_type: FileTypeGql
    content_type: str
    extension: str
    chunk_size: int

@strawberry.input
class UploadChunkInput(BaseInput):
    task_id: str
    file_id: str
    chunk_number: int
    chunk_size: int
    start_byte: int
    end_byte: int
    is_final_chunk: bool
    minio_bucket: str
    minio_object_name: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None
    max_retries: int = 3

@strawberry.input
class CompleteUploadInput(BaseInput):
    task_id: str
    file_id: str
    checksum_md5: Optional[str] = None
    checksum_sha256: Optional[str] = None

# Output types for the scenarios
@strawberry.type
class InitializeUploadResponse(BaseResponse):
    data: Optional[UploadTask] = None

@strawberry.type
class UploadChunkResponse(BaseResponse):
    data: Optional[UploadTaskFileChunk] = None

@strawberry.type
class CompleteUploadResponse(BaseResponse):
    data: Optional[UploadTaskFile] = None

@strawberry.type
class GetUploadTaskResponse(BaseResponse):
    data: Optional[UploadTask] = None

@strawberry.type
class ListUploadTasksResponse(BaseResponse):
    data: Optional[UploadTaskConnection] = None

@strawberry.type
class ListUploadTaskFilesResponse(BaseResponse):
    data: Optional[UploadTaskFileConnection] = None

@strawberry.type
class ListUploadTaskFileChunksResponse(BaseResponse):
    data: Optional[UploadTaskFileChunkConnection] = None

# Mutation implementations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def initialize_upload(self, input: InitializeUploadInput) -> InitializeUploadResponse:
        try:
            if not input.title:
                raise ValueError("Title is required")

            if input.resume_task_id:
                task = UploadTask(
                    uid=input.resume_task_id,
                    tenant_id=input.tenant_id,
                    title=input.title,
                    desc=input.desc,
                    category=None,
                    tags=[],
                    note=None,
                    status=StatusEnum.ACTIVE,
                    visibility=VisibilityEnum.PRIVATE,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    archived_at=None,
                    created_by=input.created_by,
                    allowed_users=[],
                    allowed_roles=[],
                    proc_meta=None,
                    error_info=None,
                    metadata=None,
                    proc_status=UploadProcStatusGql.PENDING,
                    source_type=input.source_type,
                    source_paths=input.source_paths,
                    upload_strategy=input.upload_strategy,
                    max_parallel_uploads=input.max_parallel_uploads,
                    chunk_size=input.chunk_size,
                    preserve_structure=input.preserve_structure,
                    base_upload_path=input.base_upload_path,
                    auto_extract_metadata=input.auto_extract_metadata,
                    file_type_filters=input.file_type_filters,
                    max_file_size=input.max_file_size,
                    discovered_files=0,
                    processing_files=0,
                    total_files=0,
                    completed_files=0,
                    failed_files=0,
                    total_size=0,
                    uploaded_size=0,
                    discovery_started_at=datetime.now(),
                    discovery_completed_at=None,
                    files=UploadTaskFileConnection(edges=[], page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=None, end_cursor=None))
                )
            else:
                task = UploadTask(
                    uid="task-uid-123",
                    tenant_id=input.tenant_id,
                    title=input.title,
                    desc=input.desc,
                    category=None,
                    tags=[],
                    note=None,
                    status=StatusEnum.ACTIVE,
                    visibility=VisibilityEnum.PRIVATE,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    archived_at=None,
                    created_by=input.created_by,
                    allowed_users=[],
                    allowed_roles=[],
                    proc_meta=None,
                    error_info=None,
                    metadata=None,
                    proc_status=UploadProcStatusGql.PENDING,
                    source_type=input.source_type,
                    source_paths=input.source_paths,
                    upload_strategy=input.upload_strategy,
                    max_parallel_uploads=input.max_parallel_uploads,
                    chunk_size=input.chunk_size,
                    preserve_structure=input.preserve_structure,
                    base_upload_path=input.base_upload_path,
                    auto_extract_metadata=input.auto_extract_metadata,
                    file_type_filters=input.file_type_filters,
                    max_file_size=input.max_file_size,
                    discovered_files=0,
                    processing_files=0,
                    total_files=0,
                    completed_files=0,
                    failed_files=0,
                    total_size=0,
                    uploaded_size=0,
                    discovery_started_at=datetime.now(),
                    discovery_completed_at=None,
                    files=UploadTaskFileConnection(edges=[], page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=None, end_cursor=None))
                )

            files = []
            if input.files:
                task.discovered_files = len(input.files)
                task.total_files = len(input.files)
                task.total_size = sum(f.file_size for f in input.files)
                for idx, file_input in enumerate(input.files):
                    file = UploadTaskFile(
                        uid=f"file-uid-{idx + 1}",
                        tenant_id=input.tenant_id,
                        master_id=task.uid,
                        note=None,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        proc_status=UploadProcStatusGql.PENDING,
                        original_path=file_input.original_path,
                        storage_path=f"{input.base_upload_path or '/uploads'}/{file_input.filename}",
                        filename=file_input.filename,
                        file_size=file_input.file_size,
                        file_type=file_input.file_type,
                        content_type=file_input.content_type,
                        extension=file_input.extension,
                        checksum_md5=None,
                        checksum_sha256=None,
                        total_chunks=(file_input.file_size + file_input.chunk_size - 1) // file_input.chunk_size,
                        uploaded_chunks=0,
                        current_chunk=0,
                        progress=0.0,
                        upload_speed=None,
                        estimated_time_remaining=None,
                        extracted_metadata=None,
                        upload_started_at=None,
                        upload_completed_at=None,
                        chunks=UploadTaskFileChunkConnection(edges=[], page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=None, end_cursor=None))
                    )
                    files.append(file)
                task.files = UploadTaskFileConnection(
                    edges=[BaseEdge(node=file, cursor=file.uid) for file in files],
                    page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=files[0].uid if files else None, end_cursor=files[-1].uid if files else None)
                )
            # In real: Save task and files to database, publish to pub/sub
            return InitializeUploadResponse(
                success=True,
                data=task,
                errors=None
            )
        except ValueError as e:
            return InitializeUploadResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_INPUT", field="title")]
            )
        except Exception as e:
            return InitializeUploadResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

    @strawberry.mutation
    async def upload_chunk(self, input: UploadChunkInput) -> UploadChunkResponse:
        try:
            if input.chunk_number < 1:
                raise ValueError("Chunk number must be positive")
            file = UploadTaskFile(
                uid=input.file_id,
                tenant_id="tenant-123",
                master_id=input.task_id,
                note=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                proc_status=UploadProcStatusGql.PENDING,
                original_path="/path/to/file.txt",
                storage_path="/uploads/file.txt",
                filename="file.txt",
                file_size=1048576,
                file_type=FileTypeGql.DOCUMENT,
                content_type="text/plain",
                extension="txt",
                checksum_md5=None,
                checksum_sha256=None,
                total_chunks=(1048576 + input.chunk_size - 1) // input.chunk_size,
                uploaded_chunks=0,
                current_chunk=0,
                progress=0.0,
                upload_speed=None,
                estimated_time_remaining=None,
                extracted_metadata=None,
                upload_started_at=datetime.now(),
                upload_completed_at=None,
                chunks=UploadTaskFileChunkConnection(edges=[], page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=None, end_cursor=None))
            )
            chunk = UploadTaskFileChunk(
                uid=f"chunk-uid-{input.chunk_number}",
                tenant_id=file.tenant_id,
                master_id=file.uid,
                note=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                proc_status=UploadProcStatusGql.IN_PROGRESS,
                file_id=input.file_id,
                chunk_number=input.chunk_number,
                chunk_size=input.chunk_size,
                start_byte=input.start_byte,
                end_byte=input.end_byte,
                is_final_chunk=input.is_final_chunk,
                minio_bucket=input.minio_bucket,
                minio_object_name=input.minio_object_name,
                minio_etag=None,
                checksum_md5=input.checksum_md5,
                checksum_sha256=input.checksum_sha256,
                retry_count=0,
                max_retries=input.max_retries
            )
            # Update file progress
            file.uploaded_chunks += 1
            file.current_chunk = input.chunk_number
            file.progress = (file.uploaded_chunks / file.total_chunks) * 100
            file.proc_status = UploadProcStatusGql.IN_PROGRESS
            file.upload_speed = 1024.0  # Mock speed in KB/s
            # In real: Save chunk, update file and task, publish updates to pub/sub
            return UploadChunkResponse(
                success=True,
                data=chunk,
                errors=None
            )
        except ValueError as e:
            return UploadChunkResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_INPUT", field="chunk_number")]
            )
        except Exception as e:
            return UploadChunkResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

    @strawberry.mutation
    async def complete_upload(self, input: CompleteUploadInput) -> CompleteUploadResponse:
        try:
            file = UploadTaskFile(
                uid=input.file_id,
                tenant_id="tenant-123",
                master_id=input.task_id,
                note=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                proc_status=UploadProcStatusGql.IN_PROGRESS,
                original_path="/path/to/file.txt",
                storage_path="/uploads/file.txt",
                filename="file.txt",
                file_size=1048576,
                file_type=FileTypeGql.DOCUMENT,
                content_type="text/plain",
                extension="txt",
                checksum_md5=input.checksum_md5,
                checksum_sha256=input.checksum_sha256,
                total_chunks=10,
                uploaded_chunks=10,
                current_chunk=10,
                progress=100.0,
                upload_speed=1024.0,
                estimated_time_remaining=0.0,
                extracted_metadata={"size": 1048576},
                upload_started_at=datetime.now(),
                upload_completed_at=None,
                chunks=UploadTaskFileChunkConnection(edges=[], page_info=RelayPageInfo(has_next_page=False, has_previous_page=False, start_cursor=None, end_cursor=None))
            )
            if file.uploaded_chunks != file.total_chunks:
                raise ValueError("Not all chunks uploaded")
            file.proc_status = UploadProcStatusGql.COMPLETED
            file.upload_completed_at = datetime.now()
            # In real: Update task completed_files, publish updates to pub/sub
            return CompleteUploadResponse(
                success=True,
                data=file,
                errors=None
            )
        except ValueError as e:
            return CompleteUploadResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_STATE", field="file_id")]
            )
        except Exception as e:
            return CompleteUploadResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

# Query implementations
@strawberry.type
class Query:
    @strawberry.field
    def get_upload_task(self, uid: str) -> GetUploadTaskResponse:
        try:
            if uid == "invalid":
                raise ValueError("Task not found")
            task = UploadTask(
                uid=uid,
                tenant_id="tenant-123",
                title="Sample Task",
                desc="Description",
                category=None,
                tags=[],
                note=None,
                status=StatusEnum.ACTIVE,
                visibility=VisibilityEnum.PRIVATE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                archived_at=None,
                created_by="user-123",
                allowed_users=[],
                allowed_roles=[],
                proc_meta=None,
                error_info=None,
                metadata=None,
                proc_status=UploadProcStatusGql.IN_PROGRESS,
                source_type=UploadSourceTypeGql.LOCAL,
                source_paths=["/path/to/file1", "/path/to/file2"],
                upload_strategy=UploadStrategyGql.PARALLEL,
                max_parallel_uploads=2,
                chunk_size=1048576,
                preserve_structure=True,
                base_upload_path="/uploads",
                auto_extract_metadata=True,
                file_type_filters=[FileTypeGql.DOCUMENT],
                max_file_size=10485760,
                discovered_files=2,
                processing_files=1,
                total_files=2,
                completed_files=1,
                failed_files=0,
                total_size=2048,
                uploaded_size=1024,
                discovery_started_at=datetime.now(),
                discovery_completed_at=None,
                files=UploadTaskFileConnection(
                    edges=[],
                    page_info=RelayPageInfo(
                        has_next_page=False,
                        has_previous_page=False,
                        start_cursor=None,
                        end_cursor=None
                    )
                )
            )
            return GetUploadTaskResponse(
                success=True,
                data=task,
                errors=None
            )
        except ValueError as e:
            return GetUploadTaskResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="NOT_FOUND", field="uid")]
            )
        except Exception as e:
            return GetUploadTaskResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

    @strawberry.field
    def list_upload_tasks(
        self,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None
    ) -> ListUploadTasksResponse:
        try:
            if first is not None and last is not None:
                raise ValueError("Cannot use both 'first' and 'last' together")
            if first is not None and first < 0:
                raise ValueError("'first' must be non-negative")
            if last is not None and last < 0:
                raise ValueError("'last' must be non-negative")

            total_tasks = 20
            all_tasks = [
                UploadTask(
                    uid=f"task-uid-{i}",
                    tenant_id="tenant-123",
                    title=f"Task {i}",
                    desc=f"Description {i}",
                    category=None,
                    tags=[],
                    note=None,
                    status=StatusEnum.ACTIVE,
                    visibility=VisibilityEnum.PRIVATE,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    archived_at=None,
                    created_by="user-123",
                    allowed_users=[],
                    allowed_roles=[],
                    proc_meta=None,
                    error_info=None,
                    metadata=None,
                    proc_status=UploadProcStatusGql.COMPLETED,
                    source_type=UploadSourceTypeGql.LOCAL,
                    source_paths=[f"/path/to/file{i}"],
                    upload_strategy=UploadStrategyGql.PARALLEL,
                    max_parallel_uploads=2,
                    chunk_size=1048576,
                    preserve_structure=True,
                    base_upload_path="/uploads",
                    auto_extract_metadata=True,
                    file_type_filters=[FileTypeGql.DOCUMENT],
                    max_file_size=10485760,
                    discovered_files=1,
                    processing_files=0,
                    total_files=1,
                    completed_files=1,
                    failed_files=0,
                    total_size=1024,
                    uploaded_size=1024,
                    discovery_started_at=datetime.now(),
                    discovery_completed_at=datetime.now(),
                    files=UploadTaskFileConnection(
                        edges=[],
                        page_info=RelayPageInfo(
                            has_next_page=False,
                            has_previous_page=False,
                            start_cursor=None,
                            end_cursor=None
                        )
                    )
                )
                for i in range(1, total_tasks + 1)
            ]

            start_index = 0
            end_index = len(all_tasks)
            if after:
                start_index = next((i for i, task in enumerate(all_tasks) if task.uid == after), -1) + 1
                if start_index == 0:
                    start_index = len(all_tasks)
            if before:
                end_index = next((i for i, task in enumerate(all_tasks) if task.uid == before), len(all_tasks))
                if end_index == -1:
                    end_index = 0

            if first is not None:
                end_index = min(start_index + first, len(all_tasks))
            elif last is not None:
                start_index = max(end_index - last, 0)

            tasks = all_tasks[start_index:end_index]
            edges = [BaseEdge(node=task, cursor=task.uid) for task in tasks]
            page_info = RelayPageInfo(
                has_next_page=end_index < len(all_tasks),
                has_previous_page=start_index > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None
            )
            connection = UploadTaskConnection(edges=edges, page_info=page_info)
            return ListUploadTasksResponse(
                success=True,
                data=connection,
                errors=None
            )
        except ValueError as e:
            return ListUploadTasksResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_INPUT", field="pagination")]
            )
        except Exception as e:
            return ListUploadTasksResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

    @strawberry.field
    def list_upload_task_files(
        self,
        task_uid: str,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None
    ) -> ListUploadTaskFilesResponse:
        try:
            if first is not None and last is not None:
                raise ValueError("Cannot use both 'first' and 'last' together")
            if first is not None and first < 0:
                raise ValueError("'first' must be non-negative")
            if last is not None and last < 0:
                raise ValueError("'last' must be non-negative")
            if task_uid == "invalid":
                raise ValueError("Task not found")

            total_files = 10
            all_files = [
                UploadTaskFile(
                    uid=f"file-uid-{i}",
                    tenant_id="tenant-123",
                    master_id=task_uid,
                    note=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    proc_status=UploadProcStatusGql.COMPLETED,
                    original_path=f"/path/to/file{i}.txt",
                    storage_path=f"/uploads/file{i}.txt",
                    filename=f"file{i}.txt",
                    file_size=1048576,
                    file_type=FileTypeGql.DOCUMENT,
                    content_type="text/plain",
                    extension="txt",
                    checksum_md5=None,
                    checksum_sha256=None,
                    total_chunks=10,
                    uploaded_chunks=10,
                    current_chunk=10,
                    progress=100.0,
                    upload_speed=1024.0,
                    estimated_time_remaining=0.0,
                    extracted_metadata={"size": 1048576},
                    upload_started_at=datetime.now(),
                    upload_completed_at=datetime.now(),
                    chunks=UploadTaskFileChunkConnection(
                        edges=[],
                        page_info=RelayPageInfo(
                            has_next_page=False,
                            has_previous_page=False,
                            start_cursor=None,
                            end_cursor=None
                        )
                    )
                )
                for i in range(1, total_files + 1)
            ]

            start_index = 0
            end_index = len(all_files)
            if after:
                start_index = next((i for i, file in enumerate(all_files) if file.uid == after), -1) + 1
                if start_index == 0:
                    start_index = len(all_files)
            if before:
                end_index = next((i for i, file in enumerate(all_files) if file.uid == before), len(all_files))
                if end_index == -1:
                    end_index = 0

            if first is not None:
                end_index = min(start_index + first, len(all_files))
            elif last is not None:
                start_index = max(end_index - last, 0)

            files = all_files[start_index:end_index]
            edges = [BaseEdge(node=file, cursor=file.uid) for file in files]
            page_info = RelayPageInfo(
                has_next_page=end_index < len(all_files),
                has_previous_page=start_index > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None
            )
            connection = UploadTaskFileConnection(edges=edges, page_info=page_info)
            return ListUploadTaskFilesResponse(
                success=True,
                data=connection,
                errors=None
            )
        except ValueError as e:
            return ListUploadTaskFilesResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_INPUT", field="pagination")]
            )
        except Exception as e:
            return ListUploadTaskFilesResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

    @strawberry.field
    def list_upload_task_file_chunks(
        self,
        file_uid: str,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None
    ) -> ListUploadTaskFileChunksResponse:
        try:
            if first is not None and last is not None:
                raise ValueError("Cannot use both 'first' and 'last' together")
            if first is not None and first < 0:
                raise ValueError("'first' must be non-negative")
            if last is not None and last < 0:
                raise ValueError("'last' must be non-negative")
            if file_uid == "invalid":
                raise ValueError("File not found")

            total_chunks = 15
            all_chunks = [
                UploadTaskFileChunk(
                    uid=f"chunk-uid-{i}",
                    tenant_id="tenant-123",
                    master_id=file_uid,
                    note=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    proc_status=UploadProcStatusGql.COMPLETED,
                    file_id=file_uid,
                    chunk_number=i,
                    chunk_size=1048576,
                    start_byte=(i - 1) * 1048576,
                    end_byte=i * 1048576,
                    is_final_chunk=i == total_chunks,
                    minio_bucket="uploads",
                    minio_object_name=f"file/{file_uid}/chunk{i}",
                    minio_etag=f"etag-{i}",
                    checksum_md5=f"md5-{i}",
                    checksum_sha256=f"sha256-{i}",
                    retry_count=0,
                    max_retries=3
                )
                for i in range(1, total_chunks + 1)
            ]

            start_index = 0
            end_index = len(all_chunks)
            if after:
                start_index = next((i for i, chunk in enumerate(all_chunks) if chunk.uid == after), -1) + 1
                if start_index == 0:
                    start_index = len(all_chunks)
            if before:
                end_index = next((i for i, chunk in enumerate(all_chunks) if chunk.uid == before), len(all_chunks))
                if end_index == -1:
                    end_index = 0

            if first is not None:
                end_index = min(start_index + first, len(all_chunks))
            elif last is not None:
                start_index = max(end_index - last, 0)

            chunks = all_chunks[start_index:end_index]
            edges = [BaseEdge(node=chunk, cursor=chunk.uid) for chunk in chunks]
            page_info = RelayPageInfo(
                has_next_page=end_index < len(all_chunks),
                has_previous_page=start_index > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None
            )
            connection = UploadTaskFileChunkConnection(edges=edges, page_info=page_info)
            return ListUploadTaskFileChunksResponse(
                success=True,
                data=connection,
                errors=None
            )
        except ValueError as e:
            return ListUploadTaskFileChunksResponse(
                success=False,
                data=None,
                errors=[Error(message=str(e), code="INVALID_INPUT", field="pagination")]
            )
        except Exception as e:
            return ListUploadTaskFileChunksResponse(
                success=False,
                data=None,
                errors=[Error(message="Unexpected error", code="SERVER_ERROR")]
            )

# Subscription implementations
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def upload_task_progress(self, task_uid: str) -> AsyncGenerator[UploadTask, None]:
        try:
            if task_uid == "invalid":
                raise ValueError("Task not found")
            # Simulate fetching initial task state
            task = UploadTask(
                uid=task_uid,
                tenant_id="tenant-123",
                title="Sample Task",
                desc="Description",
                category=None,
                tags=[],
                note=None,
                status=StatusEnum.ACTIVE,
                visibility=VisibilityEnum.PRIVATE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                archived_at=None,
                created_by="user-123",
                allowed_users=[],
                allowed_roles=[],
                proc_meta=None,
                error_info=None,
                metadata=None,
                proc_status=UploadProcStatusGql.IN_PROGRESS,
                source_type=UploadSourceTypeGql.LOCAL,
                source_paths=["/path/to/file1", "/path/to/file2"],
                upload_strategy=UploadStrategyGql.PARALLEL,
                max_parallel_uploads=2,
                chunk_size=1048576,
                preserve_structure=True,
                base_upload_path="/uploads",
                auto_extract_metadata=True,
                file_type_filters=[FileTypeGql.DOCUMENT],
                max_file_size=10485760,
                discovered_files=2,
                processing_files=1,
                total_files=2,
                completed_files=0,
                failed_files=0,
                total_size=2048,
                uploaded_size=0,
                discovery_started_at=datetime.now(),
                discovery_completed_at=None,
                files=UploadTaskFileConnection(
                    edges=[],
                    page_info=RelayPageInfo(
                        has_next_page=False,
                        has_previous_page=False,
                        start_cursor=None,
                        end_cursor=None
                    )
                )
            )
            # Simulate progress updates (in real: subscribe to pub/sub channel for task_uid)
            for i in range(5):  # Simulate 5 updates
                await asyncio.sleep(1)  # Simulate delay
                task.uploaded_size += 512  # Increment by 512 KB
                task.processing_files = max(0, task.processing_files - 1)
                task.completed_files += 1 if task.uploaded_size >= task.total_size else 0
                task.proc_status = UploadProcStatusGql.COMPLETED if task.uploaded_size >= task.total_size else UploadProcStatusGql.IN_PROGRESS
                yield task
                if task.uploaded_size >= task.total_size:
                    break
        except ValueError as e:
            raise ValueError(f"Subscription error: {str(e)}")

    @strawberry.subscription
    async def upload_task_file_progress(self, file_uid: str) -> AsyncGenerator[UploadTaskFile, None]:
        try:
            if file_uid == "invalid":
                raise ValueError("File not found")
            # Simulate fetching initial file state
            file = UploadTaskFile(
                uid=file_uid,
                tenant_id="tenant-123",
                master_id="task-uid-123",
                note=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                proc_status=UploadProcStatusGql.PENDING,
                original_path="/path/to/file.txt",
                storage_path="/uploads/file.txt",
                filename="file.txt",
                file_size=1048576,
                file_type=FileTypeGql.DOCUMENT,
                content_type="text/plain",
                extension="txt",
                checksum_md5=None,
                checksum_sha256=None,
                total_chunks=10,
                uploaded_chunks=0,
                current_chunk=0,
                progress=0.0,
                upload_speed=None,
                estimated_time_remaining=None,
                extracted_metadata=None,
                upload_started_at=datetime.now(),
                upload_completed_at=None,
                chunks=UploadTaskFileChunkConnection(
                    edges=[],
                    page_info=RelayPageInfo(
                        has_next_page=False,
                        has_previous_page=False,
                        start_cursor=None,
                        end_cursor=None
                    )
                )
            )
            # Simulate progress updates (in real: subscribe to pub/sub channel for file_uid)
            for i in range(file.total_chunks):
                await asyncio.sleep(0.5)  # Simulate delay
                file.uploaded_chunks += 1
                file.current_chunk = i + 1
                file.progress = (file.uploaded_chunks / file.total_chunks) * 100
                file.upload_speed = 2048.0  # Mock speed in KB/s
                file.estimated_time_remaining = (file.total_chunks - file.uploaded_chunks) * 0.5  # Mock ETA
                file.proc_status = UploadProcStatusGql.COMPLETED if file.uploaded_chunks == file.total_chunks else UploadProcStatusGql.IN_PROGRESS
                if file.proc_status == UploadProcStatusGql.COMPLETED:
                    file.upload_completed_at = datetime.now()
                yield file
                if file.uploaded_chunks >= file.total_chunks:
                    break
        except ValueError as e:
            raise ValueError(f"Subscription error: {str(e)}")

    @strawberry.subscription
    async def upload_task_file_chunk_progress(self, chunk_uid: str) -> AsyncGenerator[UploadTaskFileChunk, None]:
        try:
            if chunk_uid == "invalid":
                raise ValueError("Chunk not found")
            # Simulate fetching initial chunk state
            chunk = UploadTaskFileChunk(
                uid=chunk_uid,
                tenant_id="tenant-123",
                master_id="file-uid-1",
                note=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                proc_status=UploadProcStatusGql.PENDING,
                file_id="file-uid-1",
                chunk_number=1,
                chunk_size=1048576,
                start_byte=0,
                end_byte=1048576,
                is_final_chunk=False,
                minio_bucket="uploads",
                minio_object_name=f"file/file-uid-1/chunk1",
                minio_etag=None,
                checksum_md5=None,
                checksum_sha256=None,
                retry_count=0,
                max_retries=3
            )
            # Simulate progress updates (in real: subscribe to pub/sub channel for chunk_uid)
            for i in range(chunk.max_retries + 1):
                await asyncio.sleep(0.3)  # Simulate delay
                if i == chunk.max_retries:
                    chunk.proc_status = UploadProcStatusGql.FAILED
                    chunk.retry_count = i
                    yield chunk
                    break
                chunk.proc_status = UploadProcStatusGql.IN_PROGRESS if i < chunk.max_retries else UploadProcStatusGql.COMPLETED
                chunk.retry_count = i
                chunk.minio_etag = f"etag-{i+1}" if chunk.proc_status == UploadProcStatusGql.COMPLETED else None
                yield chunk
                if chunk.proc_status == UploadProcStatusGql.COMPLETED:
                    break
        except ValueError as e:
            raise ValueError(f"Subscription error: {str(e)}")

