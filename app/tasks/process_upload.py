from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from app.tasks import celery_app
from app.database import SessionLocal
from app.models import Upload, Account, Bank, Transaction
from app.parsers import get_parser
from app.services.categorization import CategorizationService
from app.utils.storage import storage


@celery_app.task(bind=True, max_retries=3)
def process_upload_task(self, upload_id: str) -> Dict[str, Any]:
    """
    Process an uploaded bank statement file.

    1. Download file from MinIO
    2. Determine parser based on bank.parser_type
    3. Parse file to extract transactions
    4. Apply categorization rules
    5. Save transactions to database
    6. Update upload status
    """
    db = SessionLocal()
    upload_uuid = UUID(upload_id)

    try:
        # Get upload record
        upload = db.query(Upload).filter(Upload.id == upload_uuid).first()
        if not upload:
            return {"error": "Upload not found"}

        # Update status to processing
        upload.status = "processing"
        db.commit()

        # Get account and bank info
        account = db.query(Account).filter(Account.id == upload.account_id).first()
        if not account:
            raise ValueError("Account not found")

        bank = db.query(Bank).filter(Bank.id == account.bank_id).first()
        if not bank:
            raise ValueError("Bank not found")

        # Download file from MinIO
        file_content = storage.download_file(upload.file_path)

        # Get appropriate parser
        parser = get_parser(bank.parser_type)
        if not parser:
            raise ValueError(f"No parser available for bank type: {bank.parser_type}")

        # Parse the file
        parsed_transactions = parser.parse(file_content, upload.filename)

        # Initialize categorization service
        categorization_service = CategorizationService(db)

        # Create transaction records
        transactions_created = 0
        for tx_data in parsed_transactions:
            # Try to categorize
            category_id = categorization_service.categorize_transaction(
                user_id=upload.user_id,
                description=tx_data.get("description"),
                counterparty=tx_data.get("counterparty"),
            )

            transaction = Transaction(
                account_id=upload.account_id,
                upload_id=upload.id,
                category_id=category_id,
                amount=tx_data["amount"],
                type=tx_data["type"],
                date=tx_data["date"],
                description=tx_data.get("description"),
                counterparty=tx_data.get("counterparty"),
                original_amount=tx_data["amount"],
                original_description=tx_data.get("description"),
                original_counterparty=tx_data.get("counterparty"),
                is_edited=False,
            )
            db.add(transaction)
            transactions_created += 1

        # Update upload status
        upload.status = "done"
        upload.processed_at = datetime.utcnow()
        db.commit()

        return {
            "upload_id": upload_id,
            "status": "done",
            "transactions_created": transactions_created,
        }

    except Exception as e:
        db.rollback()

        # Update upload status to error
        upload = db.query(Upload).filter(Upload.id == upload_uuid).first()
        if upload:
            upload.status = "error"
            upload.error_message = str(e)
            db.commit()

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return {
            "upload_id": upload_id,
            "status": "error",
            "error": str(e),
        }

    finally:
        db.close()
