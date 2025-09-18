# foxmask/knowledge/graphql/__init__.py

from .knowledge_item_resolver import KnowledgeItemQuery, KnowledgeItemMutation
from .knowledge_base_resolver import KnowledgeBaseQuery, KnowledgeBaseMutation

__all__ = [
    "KnowledgeItemQuery",
    "KnowledgeItemMutation",
    "KnowledgeBaseQuery",
    "KnowledgeBaseMutation",
]
