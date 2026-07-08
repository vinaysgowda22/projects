"""SBI (State Bank of India) email parser."""

import re
from datetime import datetime
from decimal import Decimal

from backend.parsers.base import BaseParser, TransactionDraft


class SBIParser(BaseParser):
    """Parser for SBI transaction emails."""
    
    def can_parse(self, email: dict) -> bool:
        """Check if email is from SBI."""
        sender = email.get("sender", "").lower()
        
        sbi_senders = ["alerts@sbi.co.in", "noreply@sbi.co.in", "alerts@onlinesbi.com"]
        
        return any(pattern in sender for pattern in sbi_senders)
    
    def get_sender_patterns(self) -> list[str]:
        return ["alerts@sbi.co.in", "noreply@sbi.co.in", "alerts@onlinesbi.com"]
    
    def get_subject_patterns(self) -> list[str]:
        return ["Transaction Alert", "Debit Card", "Credit Card"]
    
    def parse(self, email: dict) -> TransactionDraft:
        """Parse SBI transaction email."""
        body = email.get("body", "")
        subject = email.get("subject", "")
        
        draft = TransactionDraft()
        draft.gmail_id = email.get("gmail_id")
        draft.raw_email_subject = subject
        
        # Extract amount
        amount_match = re.search(r"(?:Rs\.?\s*|INR\s*)[\d,]+\.?\d*", body, re.IGNORECASE)
        if amount_match:
            amount_str = amount_match.group().replace("Rs.", "").replace("Rs", "").replace("INR", "").replace(",", "").strip()
            draft.amount = Decimal(amount_str)
        
        # Extract date
        date_match = re.search(r"\d{2}[-/][A-Za-z]{3}[-/]\d{4}|\d{2}[-/]\d{2}[-/]\d{4}", body)
        if date_match:
            date_str = date_match.group()
            try:
                for fmt in ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"]:
                    try:
                        draft.transaction_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Extract merchant (after "At:" or "Merchant:" or "To:")
        merchant_match = re.search(r"(?:At:|Merchant:|To:)\s*([^\n]+)", body, re.IGNORECASE)
        if merchant_match:
            draft.merchant = merchant_match.group(1).strip()
        
        # Extract reference number
        ref_match = re.search(r"Ref\.?\s*(?:No\.?\s*)?:?\s*([A-Z0-9]+)", body, re.IGNORECASE)
        if ref_match:
            draft.reference_number = ref_match.group(1)
        
        # Extract card identifier
        card_match = re.search(r"(?:card|account)\s*(?:no\.?|ending)\s*:?\s*\*{0,4}(\d{4})", body, re.IGNORECASE)
        if card_match:
            draft.account_identifier = card_match.group(1)
        
        # Determine transaction type
        if "debit" in subject.lower() or "spent" in body.lower():
            draft.transaction_type = "debit"
        elif "credit" in subject.lower() or "received" in body.lower():
            draft.transaction_type = "credit"
        
        draft.status = "posted"
        
        return draft
