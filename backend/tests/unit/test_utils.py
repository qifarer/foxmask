import pytest
from unittest.mock import AsyncMock, patch

from utils.helpers import (
    generate_uuid, get_current_time, format_timestamp,
    is_valid_object_id, convert_object_id_to_str,
    format_file_size, sanitize_filename
)
from utils.validators import validators
from utils.crypto import crypto_utils

class TestHelpers:
    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid = generate_uuid()
        assert isinstance(uuid, str)
        assert len(uuid) == 36  # UUID string length

    def test_get_current_time(self):
        """Test getting current time."""
        time = get_current_time()
        assert time is not None
        assert hasattr(time, 'tzinfo')  # Should be timezone-aware

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        from datetime import datetime, timezone
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        formatted = format_timestamp(test_time)
        
        assert isinstance(formatted, str)
        assert "2023-01-01T12:00:00" in formatted

    def test_is_valid_object_id(self):
        """Test ObjectId validation."""
        assert is_valid_object_id("507f1f77bcf86cd799439011") is True
        assert is_valid_object_id("invalid-id") is False
        assert is_valid_object_id("") is False

    def test_convert_object_id_to_str(self):
        """Test ObjectId to string conversion."""
        from bson import ObjectId
        
        test_id = ObjectId()
        test_data = {
            "id": test_id,
            "nested": {
                "object_id": test_id,
                "list": [test_id, "string", 123]
            }
        }
        
        converted = convert_object_id_to_str(test_data)
        
        assert converted["id"] == str(test_id)
        assert converted["nested"]["object_id"] == str(test_id)
        assert converted["nested"]["list"][0] == str(test_id)

    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(0) == "0B"
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1048576) == "1.00 MB"
        assert format_file_size(1073741824) == "1.00 GB"

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("../../etc/passwd") == "etcpasswd"
        assert sanitize_filename("file name with spaces.txt") == "file_name_with_spaces.txt"
        assert sanitize_filename("file@name#with$special.chars") == "filenamewithspecial.chars"

class TestValidators:
    def test_is_valid_email(self):
        """Test email validation."""
        assert validators.is_valid_email("test@example.com") is True
        assert validators.is_valid_email("invalid-email") is False
        assert validators.is_valid_email("") is False

    def test_is_valid_url(self):
        """Test URL validation."""
        assert validators.is_valid_url("https://example.com") is True
        assert validators.is_valid_url("invalid-url") is False
        assert validators.is_valid_url("") is False

    def test_is_valid_password(self):
        """Test password validation."""
        assert validators.is_valid_password("StrongPass123") is True
        assert validators.is_valid_password("weak") is False  # Too short
        assert validators.is_valid_password("nouppercase123") is False  # No uppercase
        assert validators.is_valid_password("NOLOWERCASE123") is False  # No lowercase
        assert validators.is_valid_password("NoNumbers") is False  # No numbers

    def test_sanitize_input(self):
        """Test input sanitization."""
        dangerous_input = '<script>alert("xss")</script>'
        sanitized = validators.sanitize_input(dangerous_input)
        
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert '"' not in sanitized
        assert "script" not in sanitized

class TestCryptoUtils:
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = crypto_utils.get_password_hash(password)
        
        assert crypto_utils.verify_password(password, hashed) is True
        assert crypto_utils.verify_password("wrongpassword", hashed) is False

    def test_generate_secure_random_string(self):
        """Test secure random string generation."""
        random_str = crypto_utils.generate_secure_random_string(32)
        assert isinstance(random_str, str)
        assert len(random_str) >= 32

    def test_hmac_signature(self):
        """Test HMAC signature generation and verification."""
        data = "test data"
        secret = "test secret"
        
        signature = crypto_utils.generate_hmac_signature(data, secret)
        
        assert crypto_utils.verify_hmac_signature(data, signature, secret) is True
        assert crypto_utils.verify_hmac_signature(data, "invalid-signature", secret) is False