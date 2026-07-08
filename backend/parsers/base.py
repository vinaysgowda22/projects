"""Base parser class and data structures for transaction extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class TransactionDraft:
    """Draft transaction data extracted from an email.
    
    This is an intermediate representation before database insertion.
    All fields are optional to allow partial extraction.
    """
    
    # Core transaction data
    transaction_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    
    # Bank/provided identifiers
    account_identifier: Optional[str] = None  # e.g., last 4 digits of card/account
    reference_number: Optional[str] = None
    gmail_id: Optional[str] = None
    
    # Transaction type and status
    transaction_type: Optional[str] = None  # "debit", "credit", "transfer"
    status: Optional[str] = None  # "pending", "posted"
    
    # Additional metadata
    description: Optional[str] = None
    raw_email_subject: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    result[key] = str(value)
                else:
                    result[key] = value
        return result


class BaseParser(ABC):
    """Abstract base class for bank email parsers."""
    
    @abstractmethod
    def can_parse(self, email: dict) -> bool:
        """Check if this parser can handle the given email.
        
        Args:
            email: Dictionary containing email data with keys:
                - sender: Email sender address
                - subject: Email subject line
                - body: Email body (HTML or plain text)
        
        Returns:
            True if this parser can handle the email, False otherwise.
        """
        pass
    
    @abstractmethod
    def parse(self, email: dict) -> TransactionDraft:
        """Parse transaction data from an email.
        
        Args:
            email: Dictionary containing email data with keys:
                - sender: Email sender address
                - subject: Email subject line
                - body: Email body (HTML or plain text)
                - gmail_id: Gmail message ID (if available)
        
        Returns:
            TransactionDraft with extracted data.
        
        Raises:
            ValueError: If the email cannot be parsed or required fields are missing.
        """
        pass
    
    def get_sender_patterns(self) -> list[str]:
        """Return list of sender email patterns this parser handles.
        
        Used for quick filtering by ParserRegistry.
        
        Returns:
            List of email address patterns (e.g., ["alerts@hdfcbank.com"]).
        """
        return []
    
    def get_subject_patterns(self) -> list[str]:
        """Return list of subject patterns this parser handles.
        
        Used for quick filtering by ParserRegistry.
        
        Returns:
            List of subject patterns (e.g., ["Transaction Alert", "Debit Card"]).
        """
        return []
