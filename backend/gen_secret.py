import secrets
import base64

# 生成 32 字节的随机密钥 (256 位)
secret_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
print(f"SECRET_KEY={secret_key}")