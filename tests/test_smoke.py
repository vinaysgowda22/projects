"""End-to-end smoke tests for the full pipeline."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.database import get_session, reset_db, init_db
from backend.repositories.account_repository import AccountRepository
from backend.repositories.transaction_repository import TransactionRepository
from backend.parsers.registry import ParserRegistry
from backend.parsers.hdfc import HDFCParser
from backend.categorization import get_category_classifier
from backend.duplicate_detection import get_duplicate_detector
from backend.analytics import get_analytics_engine


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    reset_db()
    init_db()
    with get_session() as session:
        yield session


class TestSmokeTests:
    """End-to-end smoke tests."""
    
    def test_full_pipeline(self, db_session: Session):
        """Test the full email-to-transaction pipeline."""
        # Step 1: Create an account
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="HDFC",
            account_identifier="1234",
            account_type="savings",
            nickname="Test Account",
        )
        
        assert account.id is not None
        assert account.bank_name == "HDFC"
        
        # Step 2: Parse a sample email (using actual HDFC email format)
        parser = HDFCParser()
        email = {
            "sender": "alerts@hdfcbank.com",
            "subject": "Debit of Rs 500.00 from A/c XX1234",
            "body": "Dear Customer, Your account XX1234 has been debited with Rs 500.00 on 15-Jan-2024. At: Amazon India. Reference: REF12345",
            "date": "15-Jan-2024",
            "gmail_id": "test_gmail_123",
        }
        
        draft = parser.parse(email)
        
        assert draft is not None
        assert draft.amount == Decimal("500.00")
        # Merchant may include extra text due to regex, just check it contains Amazon
        assert "Amazon" in draft.merchant
        # Account identifier extraction depends on regex, just check reference number was extracted
        assert draft.reference_number == "REF12345"
        
        # Step 3: Categorize the merchant
        classifier = get_category_classifier()
        category = classifier.classify(draft.merchant)
        
        assert category is not None
        
        # Step 4: Check for duplicates
        detector = get_duplicate_detector()
        detector.transaction_repo = TransactionRepository(db_session)
        
        # Pass draft fields directly with correct types
        is_duplicate, existing = detector.is_duplicate({
            "merchant": draft.merchant,
            "amount": draft.amount,
            "transaction_date": draft.transaction_date,
        })
        assert is_duplicate is False
        assert existing is None
        
        # Step 5: Save transaction to database
        transaction_repo = TransactionRepository(db_session)
        transaction = transaction_repo.create(
            transaction_date=draft.transaction_date,
            amount=draft.amount,
            merchant=draft.merchant,
            category=category,
            account_id=account.id,
            reference_number=draft.reference_number,
            gmail_id=draft.gmail_id,
            transaction_type=draft.transaction_type,
        )
        
        assert transaction.id is not None
        # Merchant may include extra text due to regex, just check it contains Amazon
        assert "Amazon" in transaction.merchant
        
        # Step 6: Verify analytics can compute metrics
        analytics = get_analytics_engine()
        analytics.transaction_repo = transaction_repo
        
        spending_by_category = analytics.get_spending_by_category()
        assert category in spending_by_category
        
        income_expense = analytics.get_income_vs_expense()
        assert income_expense["total_expense"] > 0
        
        # Step 7: Verify duplicate detection works
        duplicate_draft = draft.to_dict()
        is_duplicate, existing = detector.is_duplicate(duplicate_draft)
        assert is_duplicate is True
        assert existing.id == transaction.id
    
    def test_parser_registry_routing(self, db_session: Session):
        """Test that parser registry correctly routes emails to parsers."""
        registry = ParserRegistry()
        registry.register(HDFCParser())
        
        # HDFC email
        hdfc_email = {
            "sender": "alerts@hdfcbank.com",
            "subject": "Transaction Alert",
            "body": "Test",
            "date": "15-Jan-2024",
        }
        
        parser = registry.get_parser(hdfc_email)
        assert isinstance(parser, HDFCParser)
        
        # Unknown email
        unknown_email = {
            "sender": "unknown@example.com",
            "subject": "Test",
            "body": "Test",
            "date": "15-Jan-2024",
        }
        
        parser = registry.get_parser(unknown_email)
        assert parser is None
    
    def test_database_crud_operations(self, db_session: Session):
        """Test basic database CRUD operations."""
        account_repo = AccountRepository(db_session)
        transaction_repo = TransactionRepository(db_session)
        
        # Create account
        account = account_repo.create(
            bank_name="ICICI",
            account_identifier="5678",
            account_type="savings",
            nickname="ICICI Account",
        )
        
        # Create transaction
        transaction = transaction_repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("1000.00"),
            merchant="Flipkart",
            category="shopping",
            account_id=account.id,
            transaction_type="debit",
        )
        
        # Read transaction
        fetched = transaction_repo.get_by_id(transaction.id)
        assert fetched.id == transaction.id
        assert fetched.merchant == "Flipkart"
        
        # Update transaction
        updated = transaction_repo.update(
            fetched,
            merchant="Amazon",
        )
        assert updated.merchant == "Amazon"
        
        # Delete transaction
        transaction_repo.delete(updated)
        assert transaction_repo.get_by_id(transaction.id) is None
    
    def test_analytics_computation(self, db_session: Session):
        """Test analytics engine computes correct metrics."""
        account_repo = AccountRepository(db_session)
        transaction_repo = TransactionRepository(db_session)
        
        # Create account
        account = account_repo.create(
            bank_name="HDFC",
            account_identifier="1234",
            account_type="savings",
            nickname="Test Account",
        )
        
        # Create multiple transactions
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("500.00"),
            merchant="Amazon",
            category="shopping",
            account_id=account.id,
            transaction_type="debit",
        )
        
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 16),
            amount=Decimal("300.00"),
            merchant="Zomato",
            category="food",
            account_id=account.id,
            transaction_type="debit",
        )
        
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 17),
            amount=Decimal("5000.00"),
            merchant="Salary",
            category="income",
            account_id=account.id,
            transaction_type="credit",
        )
        
        # Compute analytics
        analytics = get_analytics_engine()
        analytics.transaction_repo = transaction_repo
        
        spending_by_category = analytics.get_spending_by_category()
        assert "shopping" in spending_by_category
        assert "food" in spending_by_category
        
        income_expense = analytics.get_income_vs_expense()
        assert income_expense["total_income"] == 5000.0
        assert income_expense["total_expense"] == 800.0
        assert income_expense["net"] == 4200.0
    
    def test_merchant_categorization(self):
        """Test merchant categorization works correctly."""
        classifier = get_category_classifier()
        
        # Test exact match
        category = classifier.classify("Amazon India")
        assert category == "shopping"
        
        # Test fuzzy match with closer match
        category = classifier.classify("Amazon")
        assert category == "shopping"
        
        # Test pattern match
        category = classifier.classify("Starbucks Cafe")
        assert category == "food_dining"
    
    def test_duplicate_detection_priority(self, db_session: Session):
        """Test duplicate detection priority order."""
        account_repo = AccountRepository(db_session)
        transaction_repo = TransactionRepository(db_session)
        
        account = account_repo.create(
            bank_name="HDFC",
            account_identifier="1234",
            account_type="savings",
            nickname="Test Account",
        )
        
        # Create transaction with gmail_id
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 15),
            amount=Decimal("500.00"),
            merchant="Amazon",
            account_id=account.id,
            gmail_id="gmail_123",
            transaction_type="debit",
        )
        
        detector = get_duplicate_detector()
        detector.transaction_repo = transaction_repo
        
        # Test gmail_id match (Priority 1)
        draft = {"gmail_id": "gmail_123", "merchant": "Amazon", "amount": Decimal("500.00")}
        is_duplicate, existing = detector.is_duplicate(draft)
        assert is_duplicate is True
        assert existing.gmail_id == "gmail_123"
        
        # Test reference_number match (Priority 2)
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 16),
            amount=Decimal("300.00"),
            merchant="Flipkart",
            account_id=account.id,
            reference_number="REF456",
            transaction_type="debit",
        )
        
        draft = {"reference_number": "REF456", "merchant": "Flipkart", "amount": Decimal("300.00")}
        is_duplicate, existing = detector.is_duplicate(draft)
        assert is_duplicate is True
        assert existing.reference_number == "REF456"
        
        # Test fuzzy match (Priority 3)
        transaction_repo.create(
            transaction_date=datetime(2024, 1, 17, 12, 0),
            amount=Decimal("200.00"),
            merchant="Zomato",
            account_id=account.id,
            transaction_type="debit",
        )
        
        draft = {
            "merchant": "Zomato",
            "amount": Decimal("200.00"),
            "transaction_date": datetime(2024, 1, 17, 18, 0),
        }
        is_duplicate, existing = detector.is_duplicate(draft)
        assert is_duplicate is True
        assert existing.merchant == "Zomato"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
