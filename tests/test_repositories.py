"""Unit tests for repository classes."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.database import get_session, init_db, reset_db
from backend.models import Account, FailedEmail, Setting, Tag, Transaction, TransactionTag
from backend.repositories import (
    AccountRepository,
    FailedEmailRepository,
    SettingRepository,
    TagRepository,
    TransactionRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Reset database to clean state
    reset_db()
    
    with get_session() as session:
        yield session


class TestAccountRepository:
    """Test suite for AccountRepository."""
    
    def test_create_account(self, db_session: Session):
        """Test creating an account."""
        repo = AccountRepository(db_session)
        account = repo.create(
            bank_name="HDFC",
            account_identifier="1234",
            account_type="savings",
            nickname="My Savings",
        )
        
        assert account.id is not None
        assert account.bank_name == "HDFC"
        assert account.account_identifier == "1234"
        assert account.account_type == "savings"
        assert account.nickname == "My Savings"
        assert account.is_active is True
    
    def test_get_by_id(self, db_session: Session):
        """Test getting account by ID."""
        repo = AccountRepository(db_session)
        account = repo.create(
            bank_name="ICICI", account_identifier="5678", account_type="checking"
        )
        
        retrieved = repo.get_by_id(account.id)
        assert retrieved is not None
        assert retrieved.id == account.id
        assert retrieved.bank_name == "ICICI"
    
    def test_get_by_bank_and_identifier(self, db_session: Session):
        """Test getting account by bank name and identifier."""
        repo = AccountRepository(db_session)
        repo.create(bank_name="Axis", account_identifier="9012", account_type="credit_card")
        
        retrieved = repo.get_by_bank_and_identifier("Axis", "9012")
        assert retrieved is not None
        assert retrieved.bank_name == "Axis"
        assert retrieved.account_identifier == "9012"
    
    def test_get_active_accounts(self, db_session: Session):
        """Test getting only active accounts."""
        repo = AccountRepository(db_session)
        repo.create(bank_name="SBI", account_identifier="1111", account_type="savings")
        repo.create(bank_name="SBI", account_identifier="2222", account_type="savings")
        inactive = repo.create(
            bank_name="SBI", account_identifier="3333", account_type="savings", is_active=False
        )
        
        active = repo.get_active_accounts()
        assert len(active) == 2
        assert inactive not in active
    
    def test_update_account(self, db_session: Session):
        """Test updating an account."""
        repo = AccountRepository(db_session)
        account = repo.create(
            bank_name="Kotak", account_identifier="4444", account_type="checking"
        )
        
        updated = repo.update(account, nickname="Updated Nickname", is_active=False)
        assert updated.nickname == "Updated Nickname"
        assert updated.is_active is False
    
    def test_delete_account(self, db_session: Session):
        """Test deleting an account."""
        repo = AccountRepository(db_session)
        account = repo.create(
            bank_name="Amex", account_identifier="5555", account_type="credit_card"
        )
        
        repo.delete(account)
        retrieved = repo.get_by_id(account.id)
        assert retrieved is None
    
    def test_count(self, db_session: Session):
        """Test counting accounts."""
        repo = AccountRepository(db_session)
        assert repo.count() == 0
        
        repo.create(bank_name="Bank1", account_identifier="1", account_type="savings")
        repo.create(bank_name="Bank2", account_identifier="2", account_type="savings")
        
        assert repo.count() == 2


class TestTransactionRepository:
    """Test suite for TransactionRepository."""
    
    def setup_method(self):
        """Create test data before each test."""
        # This will be called before each test method
    
    def test_create_transaction(self, db_session: Session):
        """Test creating a transaction."""
        # First create an account
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="HDFC", account_identifier="1234", account_type="savings"
        )
        
        # Create transaction
        tx_repo = TransactionRepository(db_session)
        transaction = tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("100.50"),
            merchant="Amazon",
            category="Shopping",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
        )
        
        assert transaction.id is not None
        assert transaction.amount == Decimal("100.50")
        assert transaction.merchant == "Amazon"
        assert transaction.category == "Shopping"
    
    def test_get_by_gmail_id(self, db_session: Session):
        """Test getting transaction by Gmail ID."""
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="ICICI", account_identifier="5678", account_type="checking"
        )
        
        tx_repo = TransactionRepository(db_session)
        transaction = tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("50.00"),
            merchant="Flipkart",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
            gmail_id="gmail123",
        )
        
        retrieved = tx_repo.get_by_gmail_id("gmail123")
        assert retrieved is not None
        assert retrieved.id == transaction.id
    
    def test_get_by_reference_number(self, db_session: Session):
        """Test getting transaction by reference number."""
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="Axis", account_identifier="9012", account_type="credit_card"
        )
        
        tx_repo = TransactionRepository(db_session)
        transaction = tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("75.00"),
            merchant="Swiggy",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
            reference_number="REF123",
        )
        
        retrieved = tx_repo.get_by_reference_number("REF123")
        assert retrieved is not None
        assert retrieved.id == transaction.id
    
    def test_search_transactions(self, db_session: Session):
        """Test searching transactions with filters."""
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="SBI", account_identifier="1111", account_type="savings"
        )
        
        tx_repo = TransactionRepository(db_session)
        tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("100.00"),
            merchant="Amazon",
            category="Shopping",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
        )
        tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("50.00"),
            merchant="Grocery Store",
            category="Groceries",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
        )
        
        # Search by merchant
        results = tx_repo.search(merchant="Amazon")
        assert len(results) == 1
        assert results[0].merchant == "Amazon"
        
        # Search by category
        results = tx_repo.search(category="Groceries")
        assert len(results) == 1
        assert results[0].category == "Groceries"
        
        # Search by amount range
        results = tx_repo.search(min_amount=Decimal("60.00"))
        assert len(results) == 1
        assert results[0].amount == Decimal("100.00")


class TestTagRepository:
    """Test suite for TagRepository."""
    
    def test_create_tag(self, db_session: Session):
        """Test creating a tag."""
        repo = TagRepository(db_session)
        tag = repo.create(name="Travel", color="#FF0000", description="Travel expenses")
        
        assert tag.id is not None
        assert tag.name == "Travel"
        assert tag.color == "#FF0000"
    
    def test_get_or_create(self, db_session: Session):
        """Test get_or_create returns existing tag."""
        repo = TagRepository(db_session)
        
        # Create tag
        tag1 = repo.get_or_create("Food", color="#00FF00")
        assert tag1.id is not None
        
        # Get existing tag
        tag2 = repo.get_or_create("Food")
        assert tag2.id == tag1.id
    
    def test_add_tag_to_transaction(self, db_session: Session):
        """Test adding a tag to a transaction."""
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="HDFC", account_identifier="1234", account_type="savings"
        )
        
        tx_repo = TransactionRepository(db_session)
        transaction = tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("100.00"),
            merchant="Test",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
        )
        
        tag_repo = TagRepository(db_session)
        tag = tag_repo.create(name="Business")
        
        transaction_tag = tag_repo.add_tag_to_transaction(transaction.id, tag.id)
        assert transaction_tag.transaction_id == transaction.id
        assert transaction_tag.tag_id == tag.id
    
    def test_get_tags_for_transaction(self, db_session: Session):
        """Test getting all tags for a transaction."""
        account_repo = AccountRepository(db_session)
        account = account_repo.create(
            bank_name="ICICI", account_identifier="5678", account_type="checking"
        )
        
        tx_repo = TransactionRepository(db_session)
        transaction = tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal("100.00"),
            merchant="Test",
            account_id=account.id,
            transaction_type="debit",
            status="posted",
        )
        
        tag_repo = TagRepository(db_session)
        tag1 = tag_repo.create(name="Tag1")
        tag2 = tag_repo.create(name="Tag2")
        
        tag_repo.add_tag_to_transaction(transaction.id, tag1.id)
        tag_repo.add_tag_to_transaction(transaction.id, tag2.id)
        
        tags = tag_repo.get_tags_for_transaction(transaction.id)
        assert len(tags) == 2
        tag_names = {t.name for t in tags}
        assert tag_names == {"Tag1", "Tag2"}


class TestSettingRepository:
    """Test suite for SettingRepository."""
    
    def test_create_setting(self, db_session: Session):
        """Test creating a setting."""
        repo = SettingRepository(db_session)
        setting = repo.create(
            key="test_key", value="test_value", description="Test setting"
        )
        
        assert setting.id is not None
        assert setting.key == "test_key"
        assert setting.value == "test_value"
    
    def test_get_by_key(self, db_session: Session):
        """Test getting setting by key."""
        repo = SettingRepository(db_session)
        repo.create(key="sync_interval", value="30", description="Sync interval in minutes")
        
        retrieved = repo.get_by_key("sync_interval")
        assert retrieved is not None
        assert retrieved.value == "30"
    
    def test_get_value_with_default(self, db_session: Session):
        """Test getting setting value with default."""
        repo = SettingRepository(db_session)
        
        # Non-existent key returns default
        value = repo.get_value("non_existent", default="default_value")
        assert value == "default_value"
        
        # Existing key returns actual value
        repo.create(key="existing_key", value="actual_value", description="Test")
        value = repo.get_value("existing_key", default="default_value")
        assert value == "actual_value"
    
    def test_set_value(self, db_session: Session):
        """Test setting a value (create or update)."""
        repo = SettingRepository(db_session)
        
        # Create new
        setting = repo.set_value("new_key", "new_value", "New setting")
        assert setting.value == "new_value"
        
        # Update existing
        updated = repo.set_value("new_key", "updated_value", "Updated description")
        assert updated.value == "updated_value"
        assert updated.description == "Updated description"
        assert updated.id == setting.id


class TestFailedEmailRepository:
    """Test suite for FailedEmailRepository."""
    
    def test_create_failed_email(self, db_session: Session):
        """Test creating a failed email record."""
        repo = FailedEmailRepository(db_session)
        failed_email = repo.create(
            gmail_id="failed123",
            sender="alerts@bank.com",
            subject="Transaction Alert",
            received_at=datetime.now(),
            failure_reason="Unknown format",
            parser_attempted="hdfc",
            processed_at=datetime.now(),
        )
        
        assert failed_email.id is not None
        assert failed_email.gmail_id == "failed123"
        assert failed_email.failure_reason == "Unknown format"
    
    def test_get_by_gmail_id(self, db_session: Session):
        """Test getting failed email by Gmail ID."""
        repo = FailedEmailRepository(db_session)
        failed_email = repo.create(
            gmail_id="failed456",
            sender="alerts@bank.com",
            subject="Alert",
            received_at=datetime.now(),
            failure_reason="Parse error",
            parser_attempted="icici",
            processed_at=datetime.now(),
        )
        
        retrieved = repo.get_by_gmail_id("failed456")
        assert retrieved is not None
        assert retrieved.id == failed_email.id
    
    def test_get_retry_candidates(self, db_session: Session):
        """Test getting emails eligible for retry."""
        repo = FailedEmailRepository(db_session)
        
        # Create failed emails with different retry counts
        repo.create(
            gmail_id="retry1",
            sender="bank1.com",
            subject="Alert1",
            received_at=datetime.now(),
            failure_reason="Error1",
            parser_attempted="hdfc",
            processed_at=datetime.now(),
            retry_count=0,
        )
        repo.create(
            gmail_id="retry2",
            sender="bank2.com",
            subject="Alert2",
            received_at=datetime.now(),
            failure_reason="Error2",
            parser_attempted="icici",
            processed_at=datetime.now(),
            retry_count=2,
        )
        repo.create(
            gmail_id="retry3",
            sender="bank3.com",
            subject="Alert3",
            received_at=datetime.now(),
            failure_reason="Error3",
            parser_attempted="axis",
            processed_at=datetime.now(),
            retry_count=5,  # Above max
        )
        
        candidates = repo.get_retry_candidates(max_retry_count=3)
        assert len(candidates) == 2
        gmail_ids = {c.gmail_id for c in candidates}
        assert gmail_ids == {"retry1", "retry2"}
    
    def test_increment_retry(self, db_session: Session):
        """Test incrementing retry count."""
        repo = FailedEmailRepository(db_session)
        failed_email = repo.create(
            gmail_id="retry_inc",
            sender="bank.com",
            subject="Alert",
            received_at=datetime.now(),
            failure_reason="Error",
            parser_attempted="hdfc",
            processed_at=datetime.now(),
            retry_count=1,
        )
        
        updated = repo.increment_retry(failed_email)
        assert updated.retry_count == 2
        assert updated.last_retry_at is not None
