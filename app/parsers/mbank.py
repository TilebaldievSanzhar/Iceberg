import io
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List

import pdfplumber

from app.parsers.base import BaseParser, ParsedTransaction


class MbankPdfParser(BaseParser):
    """
    Parser for Mbank (Kyrgyzstan) PDF bank statements.

    Expected PDF format:
    - Table with columns: Date, Description, Amount, Balance
    - Dates in format: DD.MM.YYYY
    - Amounts with +/- sign or in separate columns
    """

    def parse(self, file_content: bytes, filename: str) -> List[ParsedTransaction]:
        transactions: List[ParsedTransaction] = []

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    transactions.extend(self._parse_table(table))

        return transactions

    def _parse_table(self, table: List[List[str]]) -> List[ParsedTransaction]:
        """Parse a single table from PDF."""
        transactions: List[ParsedTransaction] = []

        if not table or len(table) < 2:
            return transactions

        # Try to find header row and determine column indices
        header_idx = self._find_header_row(table)
        if header_idx < 0:
            return transactions

        header = [str(cell).lower() if cell else "" for cell in table[header_idx]]

        # Find column indices
        date_col = self._find_column(header, ["дата", "date"])
        desc_col = self._find_column(header, ["описание", "description", "назначение"])
        amount_col = self._find_column(header, ["сумма", "amount", "приход", "расход"])
        income_col = self._find_column(header, ["приход", "credit", "зачисление"])
        expense_col = self._find_column(header, ["расход", "debit", "списание"])

        # Parse data rows
        for row in table[header_idx + 1:]:
            if not row or not any(row):
                continue

            try:
                # Parse date
                tx_date = self._parse_date(row[date_col]) if date_col >= 0 else None
                if not tx_date:
                    continue

                # Parse amount
                amount, tx_type = self._parse_amount_columns(
                    row, amount_col, income_col, expense_col
                )
                if amount is None:
                    continue

                # Parse description
                description = str(row[desc_col]).strip() if desc_col >= 0 and row[desc_col] else None

                # Extract counterparty from description
                counterparty = self._extract_counterparty(description)

                transactions.append(ParsedTransaction(
                    amount=abs(amount),
                    type=tx_type,
                    date=tx_date,
                    description=description,
                    counterparty=counterparty,
                ))

            except (IndexError, ValueError) as e:
                # Skip malformed rows
                continue

        return transactions

    def _find_header_row(self, table: List[List[str]]) -> int:
        """Find the row index that contains column headers."""
        keywords = ["дата", "date", "сумма", "amount", "описание", "description"]
        for i, row in enumerate(table[:5]):  # Check first 5 rows
            row_text = " ".join(str(cell).lower() for cell in row if cell)
            if any(kw in row_text for kw in keywords):
                return i
        return -1

    def _find_column(self, header: List[str], keywords: List[str]) -> int:
        """Find column index by header keywords."""
        for i, cell in enumerate(header):
            if any(kw in cell for kw in keywords):
                return i
        return -1

    def _parse_date(self, date_str: str) -> date:
        """Parse date string in various formats."""
        if not date_str:
            return None

        date_str = str(date_str).strip()
        formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str[:10], fmt).date()
            except ValueError:
                continue

        return None

    def _parse_amount_columns(
        self,
        row: List[str],
        amount_col: int,
        income_col: int,
        expense_col: int,
    ) -> tuple:
        """Parse amount from row, handling separate income/expense columns."""

        # Try separate columns first
        if income_col >= 0 and expense_col >= 0:
            income_val = self._clean_amount(row[income_col]) if income_col < len(row) else None
            expense_val = self._clean_amount(row[expense_col]) if expense_col < len(row) else None

            if income_val:
                return (self.parse_amount(income_val), "income")
            if expense_val:
                return (self.parse_amount(expense_val), "expense")

        # Try single amount column
        if amount_col >= 0 and amount_col < len(row):
            amount_str = self._clean_amount(row[amount_col])
            if amount_str:
                amount = self.parse_amount(amount_str)
                tx_type = self.determine_type(amount)
                return (abs(amount), tx_type)

        return (None, None)

    def _clean_amount(self, val: str) -> str:
        """Clean amount string."""
        if not val:
            return None
        val = str(val).strip()
        if not val or val == "-":
            return None
        return val

    def _extract_counterparty(self, description: str) -> str:
        """Extract counterparty from description."""
        if not description:
            return None

        # Common patterns to extract counterparty
        patterns = [
            r"от\s+(.+?)(?:\s+ИИН|\s+БИН|$)",  # от ИП Иванов
            r"в пользу\s+(.+?)(?:\s+ИИН|\s+БИН|$)",
            r"перевод\s+(?:на|от)\s+(.+?)(?:\s*$|\s+[А-Я])",
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:255]

        # Fallback: take first meaningful part
        parts = description.split()
        if len(parts) >= 2:
            return " ".join(parts[:3])[:255]

        return None
