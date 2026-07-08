"""Tests for duplicate detection."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.database import get_session, reset_db
from backend.duplicate_detection.duplicate_detector import (
    DuplicateDetector,
    get_duplicate_detector,
    reset_duplicate_detector,
)
from backend.repositories.account_repository import AccountRepository
from backend.repositories.transaction_repository import TransactionRepository


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    reset_db()
    with get_session() as session:
        yield session


@pytest.fixture(scope="function")
def test_account(db_session: Session):
    """Create a test account for each test."""
    account_repo = AccountRepository(db_session)
    return account_repo.create(
        bank_name="HDFC",
        account_identifier="1234",
        account_type="savings",
        nickname="Test Account",
    )


class TestDuplicateDetector:
    """Test suite for DuplicateDetector."""
    
    def setup_method(self):
        """Reset detector before each test."""
        reset_duplicate_detector()
    
    def test_duplicate_by_gmail_id(self, db_session: Session, test_account):
        """Test duplicate detection by gmail_id (Priority 1)."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            gmail_id="gmail_12345",
            reference_number="REF001",
            transaction_type="debit",
        )
        
        # Check for duplicate
        draft = {
            "gmail_id": "gmail_12345",
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is True
        assert found.gmail_id == "gmail_12345"
    
    def test_duplicate_by_reference_number(self, db_session: Session, test_account):
        """Test duplicate detection by reference_number (Priority 2)."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            reference_number="REF001",
            transaction_type="debit",
        )
        
        # Check for duplicate (no gmail_id)
        draft = {
            "reference_number": "REF001",
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is True
        assert found.reference_number == "REF001"
    
    def test_duplicate_by_fuzzy_match(self, db_session: Session, test_account):
        """Test duplicate detection by fuzzy match (Priority 3)."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15, 12, 0),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            transaction_type="debit",
        )
        
        # Check for duplicate (same merchant, amount, date within 24h window)
        draft = {
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15, 18, 0),  # 6 hours later
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is True
        assert found.merchant == "Amazon India"
    
    def test_no_duplicate_different_merchant(self, db_session: Session, test_account):
        """Test that different merchants are not duplicates."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            transaction_type="debit",
        )
        
        # Check for duplicate (different merchant)
        draft = {
            "merchant": "Flipkart",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is False
        assert found is None
    
    def test_no_duplicate_different_amount(self, db_session: Session, test_account):
        """Test that different amounts are not duplicates."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            transaction_type="debit",
        )
        
        # Check for duplicate (different amount)
        draft = {
            "merchant": "Amazon India",
            "amount": Decimal("500.00"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is False
        assert found is None
    
    def test_no_duplicate_outside_time_window(self, db_session: Session, test_account):
        """Test that transactions outside fuzzy time window are not duplicates."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            transaction_type="debit",
        )
        
        # Check for duplicate (same merchant/amount but 48 hours later)
        draft = {
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 17),  # 48 hours later
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is False
        assert found is None
    
    def test_exclude_transaction_id(self, db_session: Session, test_account):
        """Test that exclude_transaction_id works correctly."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create existing transaction
        created = repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            gmail_id="gmail_12345",
            transaction_type="debit",
        )
        
        # Check for duplicate, excluding the transaction itself
        draft = {
            "gmail_id": "gmail_12345",
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(
            draft,
            exclude_transaction_id=created.id,
        )
        
        assert is_duplicate is False
        assert found is None
    
    def test_find_duplicates_for_transaction(self, db_session: Session, test_account):
        """Test finding all duplicates for a transaction."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create main transaction
        created_main = repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            gmail_id="gmail_12345",
            reference_number="REF001",
            transaction_type="debit",
        )
        
        # Create duplicate by reference_number
        dup1 = repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("888.88"),
            merchant="Another Merchant",
            account_id=test_account.id,
            reference_number="REF001",  # Same reference as main
            transaction_type="debit",
        )
        
        # Create duplicate by fuzzy match
        dup2 = repo.create(
            transaction_date=datetime(2024, 1, 15, 18, 0),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            transaction_type="debit",
        )
        
        # Find duplicates
        duplicates = detector.find_duplicates_for_transaction(created_main)
        
        assert len(duplicates) == 2
        assert any(d.id == dup1.id for d in duplicates)
        assert any(d.id == dup2.id for d in duplicates)
    
    def test_priority_order_gmail_id_over_reference(self, db_session: Session, test_account):
        """Test that gmail_id match takes priority over reference_number."""
        repo = TransactionRepository(db_session)
        detector = DuplicateDetector(repo)
        
        # Create transaction with both gmail_id and reference_number
        repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1234.56"),
            merchant="Amazon India",
            account_id=test_account.id,
            gmail_id="gmail_12345",
            reference_number="REF001",
            transaction_type="debit",
        )
        
        # Check for duplicate with same gmail_id but different reference_number
        draft = {
            "gmail_id": "gmail_12345",
            "reference_number": "REF999",  # Different reference
            "merchant": "Amazon India",
            "amount": Decimal("1234.56"),
            "transaction_date": datetime(2024, 1, 15),
        }
        
        is_duplicate, found = detector.is_duplicate(draft)
        
        assert is_duplicate is True
        assert found.gmail_id == "gmail_12345"
        assert found.reference_number == "REF001"  # Original reference
    
    def test_global_singleton(self):
        """Test that global detector is a singleton."""
        detector1 = get_duplicate_detector()
        detector2 = get_duplicate_detector()
        
        assert detector1 is detector2
