from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Annotated,List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import core_schema
from pydantic.functional_validators import BeforeValidator

# 转换器
def validate_objectid(v):
    if isinstance(v, ObjectId):
        return v
    if not ObjectId.is_valid(v):
        raise ValueError("Invalid ObjectId")
    return ObjectId(v)

# 定义一个类型别名
PyObjectId = Annotated[ObjectId, BeforeValidator(validate_objectid)]


class FileMetadata(BaseModel):
    date: str
    dirname: str
    filename: str
    path: str

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True  # v2 替代 orm_mode
    )

class FileDocument(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str
    file_type: str
    hash: str
    size: int
    url: str
    metadata: FileMetadata
    knowledge_base_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True  # v2 替代 orm_mode
    )
class KnowledgeBaseDocument(BaseModel):
    id: PyObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True  # v2 替代 orm_mode
    )