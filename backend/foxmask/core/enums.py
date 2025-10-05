from enum import Enum

class Visibility(str, Enum):
    PRIVATE = "private"
    TENANT = "tenant"
    PUBLIC = "public"


class Status(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"