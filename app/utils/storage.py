import io
from typing import BinaryIO, Optional
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.config import settings


class MinIOStorage:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket: {e}")

    def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str = "application/octet-stream",
        user_id: Optional[str] = None,
    ) -> str:
        """
        Upload a file to MinIO storage.
        Returns the object path in the bucket.
        """
        # Generate unique path: user_id/uuid_filename
        unique_id = uuid4().hex[:8]
        if user_id:
            object_name = f"{user_id}/{unique_id}_{filename}"
        else:
            object_name = f"uploads/{unique_id}_{filename}"

        # Get file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start

        self.client.put_object(
            self.bucket,
            object_name,
            file,
            file_size,
            content_type=content_type,
        )

        return object_name

    def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO storage.
        Returns the file content as bytes.
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO storage.
        Returns True if successful.
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def get_file_url(self, object_name: str, expires_hours: int = 1) -> str:
        """
        Generate a presigned URL for file download.
        """
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            expires=timedelta(hours=expires_hours),
        )


# Singleton instance
storage = MinIOStorage()
