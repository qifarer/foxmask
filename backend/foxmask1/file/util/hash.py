import hashlib

def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()