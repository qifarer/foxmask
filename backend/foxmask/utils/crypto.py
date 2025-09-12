# -*- coding: utf-8 -*-
# Crypto utilitys

import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional
import secrets
from passlib.context import CryptContext
from jose import JWTError, jwt

from foxmask.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CryptoUtils:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)

    @staticmethod
    def generate_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Generate JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_jwt_token(token: str) -> Optional[dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_secure_random_string(length: int = 32) -> str:
        """Generate cryptographically secure random string"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key() -> str:
        """Generate API key"""
        return f"foxmask_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_hmac_signature(data: str, secret: str) -> str:
        """Generate HMAC signature"""
        return hmac.new(
            secret.encode(), 
            data.encode(), 
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = CryptoUtils.generate_hmac_signature(data, secret)
        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    def base64_encode(data: str) -> str:
        """Base64 encode string"""
        return base64.urlsafe_b64encode(data.encode()).decode()

    @staticmethod
    def base64_decode(encoded_data: str) -> str:
        """Base64 decode string"""
        return base64.urlsafe_b64decode(encoded_data).decode()

    @staticmethod
    def generate_file_checksum(file_path: str, algorithm: str = "md5") -> str:
        """Generate file checksum"""
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()

crypto_utils = CryptoUtils()