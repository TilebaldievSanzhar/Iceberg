from datetime import datetime
from typing import BinaryIO, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Upload, Account
from app.utils.storage import storage


class UploadService:
    def __init__(self, db: Session):
        self.db = db

    def create_upload(
        self,
        user_id: UUID,
        account_id: UUID,
        file: BinaryIO,
        filename: str,
        content_type: str,
    ) -> Upload:
        # Verify account belongs to user
        account = self.db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id,
        ).first()
        if not account:
            raise ValueError("Account not found or access denied")

        # Upload file to MinIO
        file_path = storage.upload_file(
            file=file,
            filename=filename,
            content_type=content_type,
            user_id=str(user_id),
        )

        # Create upload record
        upload = Upload(
            user_id=user_id,
            account_id=account_id,
            filename=filename,
            file_path=file_path,
            status="pending",
        )
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)

        return upload

    def get_uploads(
        self,
        user_id: UUID,
        account_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[Upload]:
        query = self.db.query(Upload).filter(Upload.user_id == user_id)

        if account_id:
            query = query.filter(Upload.account_id == account_id)
        if status:
            query = query.filter(Upload.status == status)

        return query.order_by(Upload.uploaded_at.desc()).all()

    def get_upload(self, upload_id: UUID, user_id: UUID) -> Optional[Upload]:
        return self.db.query(Upload).filter(
            Upload.id == upload_id,
            Upload.user_id == user_id,
        ).first()

    def update_status(
        self,
        upload_id: UUID,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[Upload]:
        upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            return None

        upload.status = status
        if error_message:
            upload.error_message = error_message
        if status in ("done", "error"):
            upload.processed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(upload)
        return upload

    def delete_upload(self, upload_id: UUID, user_id: UUID) -> bool:
        upload = self.get_upload(upload_id, user_id)
        if not upload:
            return False

        # Delete file from MinIO
        storage.delete_file(upload.file_path)

        # Delete from database (cascades to transactions)
        self.db.delete(upload)
        self.db.commit()
        return True

    def download_file(self, upload_id: UUID, user_id: UUID) -> Optional[bytes]:
        upload = self.get_upload(upload_id, user_id)
        if not upload:
            return None
        return storage.download_file(upload.file_path)
