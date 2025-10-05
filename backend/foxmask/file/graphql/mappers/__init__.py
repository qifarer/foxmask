# mappers/__init__.py
from .upload_mappers import UploadTaskMapper, UploadTaskFileMapper, UploadTaskFileChunkMapper
from .input_mappers import UploadTaskInputMapper, UploadTaskFileInputMapper
from .connection_mappers import UploadTaskConnectionMapper, UploadTaskFileConnectionMapper, UploadTaskFileChunkConnectionMapper
from .response_mappers import UploadResponseMapper

# 映射器注册表
MAPPER_REGISTRY = {
    'upload_task': UploadTaskMapper,
    'upload_task_file': UploadTaskFileMapper,
    'upload_task_file_chunk': UploadTaskFileChunkMapper,
    'upload_task_input': UploadTaskInputMapper,
    'upload_task_file_input': UploadTaskFileInputMapper,
    'upload_task_connection': UploadTaskConnectionMapper,
    'upload_task_file_connection': UploadTaskFileConnectionMapper,
    'upload_task_file_chunk_connection': UploadTaskFileChunkConnectionMapper,
    'upload_response': UploadResponseMapper,
}

def get_mapper(mapper_name: str):
    """获取映射器实例"""
    return MAPPER_REGISTRY.get(mapper_name)