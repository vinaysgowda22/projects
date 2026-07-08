"""HDFC Bank email parser."""

import re
from datetime import datetime
from decimal import Decimal

from backend.parsers.base import BaseParser, TransactionDraft


class HDFCParser(BaseParser):
    """Parser for HDFC Bank transaction emails."""

    def can_parse(self, email: dict) -> bool:
        """Check if email is from HDFC Bank."""
        sender = email.get("sender", "").lower()

        # HDFC sender patterns (primary check)
        hdfc_senders = ["alerts@hdfcbank.com", "noreply@hdfcbank.com"]

        return any(pattern in sender for pattern in hdfc_senders)

    def get_sender_patterns(self) -> list[str]:
        return ["alerts@hdfcbank.com", "noreply@hdfcbank.com"]

    def get_subject_patterns(self) -> list[str]:
        return ["Transaction Alert", "Debit Card", "Credit Card"]

    def parse(self, email: dict) -> TransactionDraft:
        """Parse HDFC transaction email."""
        body = email.get("body", "")
        subject = email.get("subject", "")

        draft = TransactionDraft()
        draft.gmail_id = email.get("gmail_id")
        draft.raw_email_subject = subject

        # Extract amount (e.g., "Rs. 1,234.56" or "INR 1234.56")
        amount_match = re.search(
            r"(?:Rs\.?\s*|INR\s*)[\d,]+\.?\d*", body, re.IGNORECASE
        )
        if amount_match:
            amount_str = (
                amount_match.group()
                .replace("Rs.", "")
                .replace("Rs", "")
                .replace("INR", "")
                .replace(",", "")
                .strip()
            )
            draft.amount = Decimal(amount_str)

        # Extract date (e.g., "01-Jan-2024" or "01/01/2024")
        date_match = re.search(
            r"\d{2}[-/][A-Za-z]{3}[-/]\d{4}|\d{2}[-/]\d{2}[-/]\d{4}", body
        )
        if date_match:
            date_str = date_match.group()
            try:
                # Try various date formats
                for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"]:
                    try:
                        draft.transaction_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Extract merchant (after "At:" or "Merchant:" or "To:")
        merchant_match = re.search(
            r"(?:At:|Merchant:|To:)\s*([^\n]+)", body, re.IGNORECASE
        )
        if merchant_match:
            draft.merchant = merchant_match.group(1).strip()

        # Extract reference number (handle "Ref No:", "Ref:", and "Reference:")
        ref_match = re.search(
            r"Reference:\s*([A-Z0-9]+)|Ref\.?\s*No\.?:\s*([A-Z0-9]+)|Ref\s*No\.?:\s*([A-Z0-9]+)|Ref:\s*([A-Z0-9]+)",
            body,
            re.IGNORECASE,
        )
        if ref_match:
            # Get the first non-None group
            draft.reference_number = (
                ref_match.group(1)
                or ref_match.group(2)
                or ref_match.group(3)
                or ref_match.group(4)
            )

        # Extract card/account identifier (last 4 digits)
        card_match = re.search(
            r"(?:card|account)\s*(?:no\.?|ending)\s*:?\s*\*{0,4}(\d{4})",
            body,
            re.IGNORECASE,
        )
        if card_match:
            draft.account_identifier = card_match.group(1)

        # Determine transaction type
        # Credit card transactions are debits (money leaving) unless explicitly a credit/refund
        if "credit card" in subject.lower() and "refund" not in subject.lower():
            draft.transaction_type = "debit"
        elif "debit" in subject.lower() or "spent" in body.lower():
            draft.transaction_type = "debit"
        elif "credit" in subject.lower() or "received" in body.lower():
            draft.transaction_type = "credit"

        draft.status = "posted"

        return draft
