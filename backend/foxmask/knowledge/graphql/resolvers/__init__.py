
# -*- coding: utf-8 -*-
# foxmask/knowledge/graphql/resolvers/__init__.py
"""
知识管理模块 Resolver 包
"""

from .knowledge_base import (
    KnowledgeBaseQuery,
    KnowledgeBaseMutation
)
from .knowledge_item import (
    KnowledgeItemQuery,
    KnowledgeItemMutation
)

__all__=[
    KnowledgeBaseQuery,
    KnowledgeBaseMutation,
    KnowledgeItemQuery,
    KnowledgeItemMutation
]