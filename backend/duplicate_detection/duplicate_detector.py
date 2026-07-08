"""Duplicate detection with priority order and fuzzy time-window fallback."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from loguru import logger

from backend.models.transaction import Transaction
from backend.repositories.transaction_repository import (
    TransactionRepository,
    get_transaction_repository,
)


class DuplicateDetector:
    """Detects duplicate transactions using priority order and fuzzy matching."""

    def __init__(
        self,
        transaction_repo: Optional[TransactionRepository] = None,
        fuzzy_time_window_hours: int = 24,
    ):
        """Initialize the duplicate detector.

        Args:
            transaction_repo: TransactionRepository instance. If None, uses global instance.
            fuzzy_time_window_hours: Time window in hours for fuzzy date matching.
        """
        self.transaction_repo = transaction_repo or get_transaction_repository()
        self.fuzzy_time_window = timedelta(hours=fuzzy_time_window_hours)

    def is_duplicate(
        self,
        transaction_draft: dict,
        exclude_transaction_id: Optional[int] = None,
    ) -> tuple[bool, Optional[Transaction]]:
        """Check if a transaction is a duplicate using priority order.

        Priority order:
        1. gmail_id (exact match) - highest priority
        2. reference_number (exact match)
        3. merchant + amount + date within fuzzy time window

        Args:
            transaction_draft: Transaction data dict with keys:
                - gmail_id: Optional[str]
                - reference_number: Optional[str]
                - merchant: str
                - amount: Decimal
                - transaction_date: datetime
            exclude_transaction_id: Transaction ID to exclude from duplicate check
                (useful when updating existing transactions).

        Returns:
            Tuple of (is_duplicate, existing_transaction).
            If duplicate found, existing_transaction is the matching transaction.
            Otherwise, existing_transaction is None.
        """
        gmail_id = transaction_draft.get("gmail_id")
        reference_number = transaction_draft.get("reference_number")
        merchant = transaction_draft.get("merchant")
        amount = transaction_draft.get("amount")
        transaction_date = transaction_draft.get("transaction_date")

        # Priority 1: gmail_id match
        if gmail_id:
            existing = self._find_by_gmail_id(gmail_id, exclude_transaction_id)
            if existing:
                logger.debug(f"Duplicate found by gmail_id: {gmail_id}")
                return True, existing

        # Priority 2: reference_number match
        if reference_number:
            existing = self._find_by_reference_number(
                reference_number, exclude_transaction_id
            )
            if existing:
                logger.debug(f"Duplicate found by reference_number: {reference_number}")
                return True, existing

        # Priority 3: fuzzy match (merchant + amount + date within window)
        if merchant and amount and transaction_date:
            existing = self._find_by_fuzzy_match(
                merchant,
                amount,
                transaction_date,
                exclude_transaction_id,
            )
            if existing:
                logger.debug(
                    f"Potential duplicate found by fuzzy match: "
                    f"merchant={merchant}, amount={amount}, date={transaction_date}"
                )
                return True, existing

        return False, None

    def _find_by_gmail_id(
        self,
        gmail_id: str,
        exclude_transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        """Find transaction by gmail_id."""
        session = self.transaction_repo.session
        query = session.query(Transaction).filter(Transaction.gmail_id == gmail_id)

        if exclude_transaction_id:
            query = query.filter(Transaction.id != exclude_transaction_id)

        return query.first()

    def _find_by_reference_number(
        self,
        reference_number: str,
        exclude_transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        """Find transaction by reference_number."""
        session = self.transaction_repo.session
        query = session.query(Transaction).filter(
            Transaction.reference_number == reference_number
        )

        if exclude_transaction_id:
            query = query.filter(Transaction.id != exclude_transaction_id)

        return query.first()

    def _find_by_fuzzy_match(
        self,
        merchant: str,
        amount: Decimal,
        transaction_date: datetime,
        exclude_transaction_id: Optional[int] = None,
    ) -> Optional[Transaction]:
        """Find transaction by merchant, amount, and date within fuzzy window."""
        date_start = transaction_date - self.fuzzy_time_window
        date_end = transaction_date + self.fuzzy_time_window

        session = self.transaction_repo.session
        query = session.query(Transaction).filter(
            Transaction.merchant == merchant,
            Transaction.amount == amount,
            Transaction.transaction_date >= date_start,
            Transaction.transaction_date <= date_end,
        )

        if exclude_transaction_id:
            query = query.filter(Transaction.id != exclude_transaction_id)

        return query.first()

    def find_duplicates_for_transaction(
        self,
        transaction: Transaction,
    ) -> list[Transaction]:
        """Find all potential duplicates for an existing transaction.

        Useful for identifying and cleaning up duplicate data.

        Args:
            transaction: The transaction to find duplicates for.

        Returns:
            List of duplicate transactions.
        """
        duplicates = []
        session = self.transaction_repo.session

        # Check by gmail_id
        if transaction.gmail_id:
            gmail_matches = (
                session.query(Transaction)
                .filter(
                    Transaction.gmail_id == transaction.gmail_id,
                    Transaction.id != transaction.id,
                )
                .all()
            )
            duplicates.extend(gmail_matches)

        # Check by reference_number
        if transaction.reference_number:
            ref_matches = (
                session.query(Transaction)
                .filter(
                    Transaction.reference_number == transaction.reference_number,
                    Transaction.id != transaction.id,
                )
                .all()
            )
            duplicates.extend(ref_matches)

        # Check by fuzzy match
        date_start = transaction.transaction_date - self.fuzzy_time_window
        date_end = transaction.transaction_date + self.fuzzy_time_window

        fuzzy_matches = (
            session.query(Transaction)
            .filter(
                Transaction.merchant == transaction.merchant,
                Transaction.amount == transaction.amount,
                Transaction.transaction_date >= date_start,
                Transaction.transaction_date <= date_end,
                Transaction.id != transaction.id,
            )
            .all()
        )

        # Add fuzzy matches that aren't already in duplicates
        for match in fuzzy_matches:
            if match not in duplicates:
                duplicates.append(match)

        return duplicates


# Global detector instance
_detector: Optional[DuplicateDetector] = None


def get_duplicate_detector() -> DuplicateDetector:
    """Get the global duplicate detector instance (singleton pattern)."""
    global _detector
    if _detector is None:
        _detector = DuplicateDetector()
    return _detector


def reset_duplicate_detector() -> None:
    """Reset the global duplicate detector (useful for testing)."""
    global _detector
    _detector = None
