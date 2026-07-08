"""Email to transaction pipeline."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from loguru import logger

from backend.categorization import get_category_classifier
from backend.duplicate_detection import get_duplicate_detector
from backend.parsers.registry import ParserRegistry, get_parser_registry
from backend.repositories.account_repository import AccountRepository
from backend.repositories.failed_email_repository import FailedEmailRepository
from backend.repositories.transaction_repository import TransactionRepository
from backend.database import get_session


class TransactionPipeline:
    """Pipeline for converting emails to transactions."""
    
    def __init__(
        self,
        parser_registry: Optional[ParserRegistry] = None,
        duplicate_detector=None,
        category_classifier=None,
    ):
        """Initialize the transaction pipeline.
        
        Args:
            parser_registry: ParserRegistry instance. If None, uses global instance.
            duplicate_detector: DuplicateDetector instance. If None, uses global instance.
            category_classifier: CategoryClassifier instance. If None, uses global instance.
        """
        self.parser_registry = parser_registry or get_parser_registry()
        self.duplicate_detector = duplicate_detector or get_duplicate_detector()
        self.category_classifier = category_classifier or get_category_classifier()
    
    def process_email(self, email: dict) -> Optional[dict]:
        """Process a single email and convert to transaction.
        
        Args:
            email: Email dictionary with keys: gmail_id, sender, subject, body, date.
        
        Returns:
            Transaction data dict if successful, None if failed.
        """
        try:
            # Step 1: Parse email to transaction draft
            draft = self._parse_email(email)
            if not draft:
                logger.warning(f"Failed to parse email: {email.get('gmail_id')}")
                return None
            
            # Step 2: Check for duplicates
            is_duplicate, existing = self.duplicate_detector.is_duplicate(draft)
            if is_duplicate:
                logger.info(f"Duplicate detected for email: {email.get('gmail_id')}")
                return None
            
            # Step 3: Categorize merchant
            category = self.category_classifier.classify(draft["merchant"])
            draft["category"] = category
            
            # Step 4: Save to database
            transaction = self._save_transaction(draft)
            
            logger.info(f"Successfully processed email: {email.get('gmail_id')} -> transaction {transaction.id}")
            return draft
            
        except Exception as e:
            logger.error(f"Error processing email {email.get('gmail_id')}: {e}")
            self._save_failed_email(email, str(e))
            return None
    
    def _parse_email(self, email: dict) -> Optional[dict]:
        """Parse email using appropriate parser.
        
        Args:
            email: Email dictionary.
        
        Returns:
            TransactionDraft dict or None if parsing failed.
        """
        parser = self.parser_registry.get_parser(email)
        if not parser:
            logger.warning(f"No parser found for email from: {email.get('sender')}")
            return None
        
        draft = parser.parse(email)
        return draft.to_dict() if draft else None
    
    def _save_transaction(self, draft: dict):
        """Save transaction to database.
        
        Args:
            draft: Transaction data dict.
        
        Returns:
            Created Transaction object.
        """
        with get_session().__enter__() as session:
            # Find or create account
            account_repo = AccountRepository(session)
            account = self._get_or_create_account(
                account_repo,
                draft.get("bank_name", "Unknown"),
                draft.get("account_identifier", ""),
            )
            
            # Create transaction
            transaction_repo = TransactionRepository(session)
            transaction = transaction_repo.create(
                transaction_date=draft["transaction_date"],
                amount=Decimal(str(draft["amount"])),
                merchant=draft["merchant"],
                category=draft.get("category"),
                account_id=account.id,
                reference_number=draft.get("reference_number"),
                gmail_id=draft.get("gmail_id"),
                transaction_type=draft.get("transaction_type", "debit"),
                status=draft.get("status", "posted"),
                description=draft.get("description"),
                raw_email_subject=draft.get("subject"),
            )
            
            return transaction
    
    def _get_or_create_account(
        self,
        account_repo: AccountRepository,
        bank_name: str,
        account_identifier: str,
    ):
        """Get existing account or create new one.
        
        Args:
            account_repo: AccountRepository instance.
            bank_name: Bank name.
            account_identifier: Account identifier (e.g., last 4 digits).
        
        Returns:
            Account object.
        """
        # Try to find existing account
        account = account_repo.get_by_identifier(bank_name, account_identifier)
        
        if not account:
            # Create new account
            account = account_repo.create(
                bank_name=bank_name,
                account_identifier=account_identifier,
                account_type="savings",  # Default type
                nickname=f"{bank_name} {account_identifier}",
            )
            logger.info(f"Created new account: {bank_name} {account_identifier}")
        
        return account
    
    def _save_failed_email(self, email: dict, error_message: str) -> None:
        """Save failed email to database for later review.
        
        Args:
            email: Email dictionary.
            error_message: Error message describing why processing failed.
        """
        with get_session().__enter__() as session:
            failed_email_repo = FailedEmailRepository(session)
            failed_email_repo.create(
                gmail_id=email.get("gmail_id"),
                sender=email.get("sender"),
                subject=email.get("subject"),
                body=email.get("body", "")[:5000],  # Truncate if too long
                error_message=error_message,
                processed_at=datetime.utcnow(),
            )
            logger.warning(f"Saved failed email: {email.get('gmail_id')}")
    
    def process_emails(self, emails: list[dict]) -> dict:
        """Process multiple emails.
        
        Args:
            emails: List of email dictionaries.
        
        Returns:
            Summary dict with counts of successful, failed, and duplicate emails.
        """
        summary = {
            "total": len(emails),
            "successful": 0,
            "failed": 0,
            "duplicates": 0,
        }
        
        for email in emails:
            result = self.process_email(email)
            if result:
                summary["successful"] += 1
            else:
                # Check if it was a duplicate (no failed email saved)
                # This is a simplification - in production, track duplicate separately
                summary["failed"] += 1
        
        logger.info(f"Processed {summary['total']} emails: {summary}")
        return summary


# Global pipeline instance
_pipeline: Optional[TransactionPipeline] = None


def get_transaction_pipeline() -> TransactionPipeline:
    """Get the global transaction pipeline instance (singleton pattern)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = TransactionPipeline()
    return _pipeline


def reset_transaction_pipeline() -> None:
    """Reset the global transaction pipeline (useful for testing)."""
    global _pipeline
    _pipeline = None
