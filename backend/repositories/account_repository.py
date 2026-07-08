"""Repository for Account model."""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.account import Account
from backend.repositories.base_repository import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account operations."""
    
    def __init__(self, session: Session):
        """Initialize AccountRepository."""
        super().__init__(Account, session)
    
    def get_by_bank_and_identifier(
        self, bank_name: str, account_identifier: str
    ) -> Optional[Account]:
        """Get account by bank name and account identifier."""
        return (
            self.session.query(Account)
            .filter(Account.bank_name == bank_name, Account.account_identifier == account_identifier)
            .first()
        )
    
    def get_active_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return self.session.query(Account).filter(Account.is_active == True).all()
    
    def get_by_bank_name(self, bank_name: str) -> List[Account]:
        """Get all accounts for a specific bank."""
        return self.session.query(Account).filter(Account.bank_name == bank_name).all()
