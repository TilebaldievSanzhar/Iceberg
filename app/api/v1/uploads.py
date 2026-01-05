from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User, Upload, Transaction
from app.schemas import UploadResponse
from app.services import UploadService
from app.tasks.process_upload import process_upload_task

router = APIRouter()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    account_id: UUID = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a bank statement file for processing."""
    # Validate file type
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: PDF, Excel, CSV",
        )

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB",
        )

    try:
        service = UploadService(db)
        import io
        upload = service.create_upload(
            user_id=current_user.id,
            account_id=account_id,
            file=io.BytesIO(content),
            filename=file.filename,
            content_type=file.content_type,
        )

        # Queue processing task
        process_upload_task.delay(str(upload.id))

        return upload

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=List[UploadResponse])
def get_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    account_id: Optional[UUID] = None,
    upload_status: Optional[str] = None,
):
    """Get upload history."""
    service = UploadService(db)
    uploads = service.get_uploads(
        user_id=current_user.id,
        account_id=account_id,
        status=upload_status,
    )

    # Add transaction count to each upload
    for upload in uploads:
        count = db.query(Transaction).filter(
            Transaction.upload_id == upload.id
        ).count()
        upload.transaction_count = count

    return uploads


@router.get("/{upload_id}", response_model=UploadResponse)
def get_upload(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get upload status by ID."""
    service = UploadService(db)
    upload = service.get_upload(upload_id, current_user.id)

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )

    # Add transaction count
    count = db.query(Transaction).filter(
        Transaction.upload_id == upload.id
    ).count()
    upload.transaction_count = count

    return upload


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete upload and all associated transactions."""
    service = UploadService(db)
    success = service.delete_upload(upload_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
