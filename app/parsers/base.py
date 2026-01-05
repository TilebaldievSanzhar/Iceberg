from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import List, TypedDict, Optional


class ParsedTransaction(TypedDict):
    amount: Decimal
    type: str  # "income", "expense", "transfer"
    date: date
    description: Optional[str]
    counterparty: Optional[str]


class BaseParser(ABC):
    """Base class for bank statement parsers."""

    @abstractmethod
    def parse(self, file_content: bytes, filename: str) -> List[ParsedTransaction]:
        """
        Parse a bank statement file and extract transactions.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename (used to determine file type)

        Returns:
            List of parsed transactions
        """
        pass

    def get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def parse_amount(self, amount_str: str) -> Decimal:
        """
        Parse amount string to Decimal.
        Handles various formats: "1,234.56", "1 234,56", "-1234.56"
        """
        # Remove spaces and replace comma with dot
        cleaned = amount_str.replace(" ", "").replace(",", ".")

        # Handle thousands separator (if both . and , were present)
        parts = cleaned.split(".")
        if len(parts) > 2:
            # Multiple dots means the first ones are thousands separators
            cleaned = "".join(parts[:-1]) + "." + parts[-1]

        return Decimal(cleaned)

    def determine_type(self, amount: Decimal) -> str:
        """Determine transaction type based on amount sign."""
        if amount > 0:
            return "income"
        elif amount < 0:
            return "expense"
        return "transfer"
