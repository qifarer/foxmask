import strawberry
from foxmask.file.graphql.resolvers import (
    FileMutation,
    FileQuery,
    UploadQuery,
    UploadMutation,
)
from foxmask.knowledge.graphql.resolvers import (
    KnowledgeBaseQuery,
    KnowledgeBaseMutation,
    KnowledgeItemQuery,
    KnowledgeItemMutation,
    
)


@strawberry.type
class Mutation:
    """根变更类型"""
    file: FileMutation = strawberry.field(resolver=lambda: FileMutation())
    upload: UploadMutation = strawberry.field(resolver=lambda: UploadMutation())
    knowledge_item: KnowledgeItemMutation = strawberry.field(resolver=lambda: KnowledgeItemMutation())
    knowledge_base: KnowledgeBaseMutation = strawberry.field(resolver=lambda: KnowledgeBaseMutation())


@strawberry.type
class Query:
    """根查询类型"""
    file: FileQuery = strawberry.field(resolver=lambda: FileQuery())
    upload: UploadQuery = strawberry.field(resolver=lambda: UploadQuery())
    knowledge_item: KnowledgeItemQuery = strawberry.field(resolver=lambda: KnowledgeItemQuery())
    knowledge_base: KnowledgeBaseQuery = strawberry.field(resolver=lambda: KnowledgeBaseQuery())


# 创建GraphQL Schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)


