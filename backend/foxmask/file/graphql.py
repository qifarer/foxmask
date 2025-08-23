# foxmask/file/graphql.py
import strawberry
from typing import List, Optional
from foxmask.file.models import FileMetadata, FileStatus
from foxmask.file.services import FileService
from foxmask.auth.dependencies import get_current_user

@strawberry.type
class File:
    id: strawberry.ID
    filename: str
    size: int
    content_type: str
    status: str
    owner: str
    uploaded_at: str
    url: Optional[str] = None

@strawberry.input
class FileUploadInput:
    filename: str
    size: int
    content_type: str

@strawberry.type
class FileMutation:
    @strawberry.mutation
    async def initiate_upload(self, info, input: FileUploadInput) -> str:
        user = await get_current_user(info.context["request"])
        service = FileService()
        file_id = await service.initiate_upload(
            input.filename, 
            input.size, 
            input.content_type,
            user.id
        )
        return file_id

@strawberry.type
class FileQuery:
    @strawberry.field
    async def files(self, info) -> List[File]:
        user = await get_current_user(info.context["request"])
        service = FileService()
        files = await service.list_files(user.id)
        return [File(**file.dict()) for file in files]