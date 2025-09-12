# -*- coding: utf-8 -*-
# Validators for various data types

import re
from typing import Optional, List
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlparse

class Validators:
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number (basic international format)"""
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """Validate username"""
        pattern = r'^[a-zA-Z0-9_\-]{3,50}$'
        return bool(re.match(pattern, username))

    @staticmethod
    def is_valid_password(password: str) -> bool:
        """Validate password strength"""
        if len(password) < 8:
            return False
        if not any(char.isdigit() for char in password):
            return False
        if not any(char.isupper() for char in password):
            return False
        if not any(char.islower() for char in password):
            return False
        return True

    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        """Validate UUID format"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))

    @staticmethod
    def is_valid_ip_address(ip: str) -> bool:
        """Validate IP address"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        # Check each octet
        octets = ip.split('.')
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                return False
        
        return True

    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """Validate domain name"""
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain))

    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 500) -> str:
        """Sanitize user input"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'&;]', '', input_str)
        # Trim to max length
        return sanitized[:max_length].strip()

validators = Validators()