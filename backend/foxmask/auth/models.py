# app/domains/auth/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    id: str
    username: str
    email: Optional[EmailStr] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None