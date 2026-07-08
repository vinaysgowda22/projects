"""Repository for Transaction model."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.models.transaction import Transaction
from backend.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction operations."""
    
    def __init__(self, session: Session):
        """Initialize TransactionRepository."""
        super().__init__(Transaction, session)
    
    def get_by_gmail_id(self, gmail_id: str) -> Optional[Transaction]:
        """Get transaction by Gmail ID."""
        return self.session.query(Transaction).filter(Transaction.gmail_id == gmail_id).first()
    
    def get_by_reference_number(self, reference_number: str) -> Optional[Transaction]:
        """Get transaction by bank reference number."""
        return (
            self.session.query(Transaction)
            .filter(Transaction.reference_number == reference_number)
            .first()
        )
    
    def get_by_date_range(
        self, start_date: datetime, end_date: datetime, account_id: Optional[int] = None
    ) -> List[Transaction]:
        """Get transactions within a date range, optionally filtered by account."""
        query = self.session.query(Transaction).filter(
            Transaction.transaction_date >= start_date, Transaction.transaction_date <= end_date
        )
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        return query.order_by(Transaction.transaction_date.desc()).all()
    
    def get_by_merchant(self, merchant: str, limit: int = 100) -> List[Transaction]:
        """Get transactions by merchant name (case-insensitive)."""
        return (
            self.session.query(Transaction)
            .filter(Transaction.merchant.ilike(f"%{merchant}%"))
            .limit(limit)
            .all()
        )
    
    def get_by_category(self, category: str, limit: int = 100) -> List[Transaction]:
        """Get transactions by category."""
        return (
            self.session.query(Transaction)
            .filter(Transaction.category == category)
            .limit(limit)
            .all()
        )
    
    def get_duplicates(self) -> List[Transaction]:
        """Get all transactions marked as duplicates."""
        return self.session.query(Transaction).filter(Transaction.is_duplicate == True).all()
    
    def get_possible_duplicates(self) -> List[Transaction]:
        """Get transactions flagged as possible duplicates."""
        return (
            self.session.query(Transaction).filter(Transaction.possible_duplicate == True).all()
        )
    
    def search(
        self,
        merchant: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        account_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Transaction]:
        """Search transactions with multiple filters."""
        query = self.session.query(Transaction)
        
        if merchant:
            query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))
        if category:
            query = query.filter(Transaction.category == category)
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if min_amount:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount:
            query = query.filter(Transaction.amount <= max_amount)
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        
        return query.order_by(Transaction.transaction_date.desc()).limit(limit).all()
    
    def get_recent(self, limit: int = 50) -> List[Transaction]:
        """Get recent transactions."""
        return (
            self.session.query(Transaction)
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
            .all()
        )


# Global repository instance
_repository: Optional[TransactionRepository] = None


def get_transaction_repository() -> TransactionRepository:
    """Get the global transaction repository instance (singleton pattern)."""
    global _repository
    if _repository is None:
        _repository = TransactionRepository(get_session().__enter__())
    return _repository


def reset_transaction_repository() -> None:
    """Reset the global transaction repository (useful for testing)."""
    global _repository
    _repository = None
