import io
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List

import pandas as pd
import pdfplumber

from app.parsers.base import BaseParser, ParsedTransaction


class BakaiBankParser(BaseParser):
    """
    Parser for Bakai Bank (Kyrgyzstan) statements.
    Supports both PDF and Excel formats.
    """

    def parse(self, file_content: bytes, filename: str) -> List[ParsedTransaction]:
        ext = self.get_file_extension(filename)

        if ext in ("xlsx", "xls"):
            return self._parse_excel(file_content)
        elif ext == "pdf":
            return self._parse_pdf(file_content)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _parse_excel(self, file_content: bytes) -> List[ParsedTransaction]:
        """Parse Excel bank statement."""
        transactions: List[ParsedTransaction] = []

        df = pd.read_excel(io.BytesIO(file_content))

        # Normalize column names
        df.columns = [str(col).lower().strip() for col in df.columns]

        # Find relevant columns
        date_col = self._find_df_column(df, ["дата", "date", "дата операции"])
        desc_col = self._find_df_column(df, ["описание", "description", "назначение", "детали"])
        amount_col = self._find_df_column(df, ["сумма", "amount"])
        income_col = self._find_df_column(df, ["приход", "credit", "зачисление", "дебет"])
        expense_col = self._find_df_column(df, ["расход", "debit", "списание", "кредит"])

        for _, row in df.iterrows():
            try:
                # Parse date
                tx_date = self._parse_excel_date(row.get(date_col))
                if not tx_date:
                    continue

                # Parse amount
                if income_col and expense_col:
                    income_val = self._parse_excel_amount(row.get(income_col))
                    expense_val = self._parse_excel_amount(row.get(expense_col))

                    if income_val and income_val > 0:
                        amount, tx_type = income_val, "income"
                    elif expense_val and expense_val > 0:
                        amount, tx_type = expense_val, "expense"
                    else:
                        continue
                elif amount_col:
                    amount = self._parse_excel_amount(row.get(amount_col))
                    if not amount:
                        continue
                    tx_type = "income" if amount > 0 else "expense"
                    amount = abs(amount)
                else:
                    continue

                # Parse description
                description = str(row.get(desc_col, "")).strip() or None
                counterparty = self._extract_counterparty(description)

                transactions.append(ParsedTransaction(
                    amount=amount,
                    type=tx_type,
                    date=tx_date,
                    description=description,
                    counterparty=counterparty,
                ))

            except Exception:
                continue

        return transactions

    def _parse_pdf(self, file_content: bytes) -> List[ParsedTransaction]:
        """Parse PDF bank statement."""
        transactions: List[ParsedTransaction] = []

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    transactions.extend(self._parse_pdf_table(table))

        return transactions

    def _parse_pdf_table(self, table: List[List[str]]) -> List[ParsedTransaction]:
        """Parse a single table from PDF."""
        transactions: List[ParsedTransaction] = []

        if not table or len(table) < 2:
            return transactions

        # Find header row
        header_idx = -1
        for i, row in enumerate(table[:5]):
            row_text = " ".join(str(cell).lower() for cell in row if cell)
            if "дата" in row_text or "date" in row_text:
                header_idx = i
                break

        if header_idx < 0:
            return transactions

        header = [str(cell).lower() if cell else "" for cell in table[header_idx]]

        # Find column indices
        date_col = next((i for i, h in enumerate(header) if "дата" in h or "date" in h), -1)
        desc_col = next((i for i, h in enumerate(header) if "опис" in h or "назнач" in h), -1)
        amount_col = next((i for i, h in enumerate(header) if "сумма" in h or "amount" in h), -1)

        # Parse rows
        for row in table[header_idx + 1:]:
            if not row or len(row) <= max(date_col, desc_col, amount_col):
                continue

            try:
                date_str = str(row[date_col]).strip() if date_col >= 0 else None
                tx_date = self._parse_date_str(date_str)
                if not tx_date:
                    continue

                amount_str = str(row[amount_col]).strip() if amount_col >= 0 else None
                if not amount_str or amount_str == "-":
                    continue

                amount = self.parse_amount(amount_str)
                tx_type = self.determine_type(amount)

                description = str(row[desc_col]).strip() if desc_col >= 0 else None
                counterparty = self._extract_counterparty(description)

                transactions.append(ParsedTransaction(
                    amount=abs(amount),
                    type=tx_type,
                    date=tx_date,
                    description=description,
                    counterparty=counterparty,
                ))

            except Exception:
                continue

        return transactions

    def _find_df_column(self, df: pd.DataFrame, keywords: List[str]) -> str:
        """Find column name in DataFrame by keywords."""
        for col in df.columns:
            for kw in keywords:
                if kw in str(col).lower():
                    return col
        return None

    def _parse_excel_date(self, val) -> date:
        """Parse date from Excel cell."""
        if val is None or pd.isna(val):
            return None

        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val

        return self._parse_date_str(str(val))

    def _parse_excel_amount(self, val) -> Decimal:
        """Parse amount from Excel cell."""
        if val is None or pd.isna(val):
            return None

        if isinstance(val, (int, float)):
            return Decimal(str(val))

        val_str = str(val).strip()
        if not val_str or val_str == "-":
            return None

        return self.parse_amount(val_str)

    def _parse_date_str(self, date_str: str) -> date:
        """Parse date string."""
        if not date_str:
            return None

        formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:10], fmt).date()
            except ValueError:
                continue

        return None

    def _extract_counterparty(self, description: str) -> str:
        """Extract counterparty from transaction description."""
        if not description:
            return None

        # Clean up common prefixes
        description = re.sub(r"^(Оплата|Перевод|Покупка|Снятие|Пополнение)\s*:?\s*", "", description, flags=re.I)

        # Extract merchant/counterparty name
        patterns = [
            r"от\s+(.+?)(?:\s*$|\s+на\s)",
            r"в\s+(.+?)(?:\s*$|\s+за\s)",
            r"^([A-Za-zА-Яа-я\s]+?)(?:\s+\d|\s*$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                counterparty = match.group(1).strip()
                if len(counterparty) > 2:
                    return counterparty[:255]

        # Fallback: take first few words
        words = description.split()[:3]
        if words:
            return " ".join(words)[:255]

        return None
