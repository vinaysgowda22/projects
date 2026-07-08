"""Repository for Budget model."""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.budget import Budget
from backend.repositories.base_repository import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Repository for Budget operations."""

    def __init__(self, session: Session):
        """Initialize BudgetRepository."""
        super().__init__(Budget, session)

    def get_by_category(
        self, category: str, period: str = "monthly"
    ) -> Optional[Budget]:
        """Get the budget for a category and period, if any."""
        return (
            self.session.query(Budget)
            .filter(Budget.category == category, Budget.period == period)
            .first()
        )

    def get_active(self) -> List[Budget]:
        """Get all active budgets."""
        return self.session.query(Budget).filter(Budget.is_active.is_(True)).all()

    def upsert(self, category: str, amount, period: str = "monthly") -> Budget:
        """Create or update the budget for a category/period."""
        budget = self.get_by_category(category, period)
        if budget:
            return self.update(budget, amount=amount)
        return self.create(
            category=category, amount=amount, period=period, is_active=True
        )
