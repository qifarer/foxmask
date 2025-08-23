# foxmask/core/minio.py
from minio import Minio
from minio.error import S3Error
from foxmask.core.config import get_settings

settings = get_settings()

def get_minio_client():
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

async def ensure_bucket_exists(minio_client: Minio, bucket_name: str = None):
    bucket_name = bucket_name or settings.MINIO_BUCKET
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
    except S3Error as e:
        print(f"Error creating bucket {bucket_name}: {e}")