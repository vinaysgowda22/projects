"""Tests for the Budget model, repository, and budget-vs-actual analytics."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from backend.analytics.analytics_engine import AnalyticsEngine
from backend.database import get_session, reset_db
from backend.repositories import (
    AccountRepository,
    BudgetRepository,
    TransactionRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    reset_db()
    with get_session() as session:
        yield session


class TestBudgetRepository:
    """Test suite for BudgetRepository."""

    def test_create_and_get_by_category(self, db_session: Session):
        repo = BudgetRepository(db_session)
        budget = repo.create(
            category="food_dining", amount=Decimal("5000"), period="monthly"
        )
        assert budget.id is not None
        assert repo.get_by_category("food_dining").amount == Decimal("5000")

    def test_upsert_updates_existing(self, db_session: Session):
        repo = BudgetRepository(db_session)
        repo.upsert("shopping", Decimal("3000"))
        repo.upsert("shopping", Decimal("4500"))
        budgets = repo.get_all()
        assert len(budgets) == 1
        assert budgets[0].amount == Decimal("4500")

    def test_get_active_excludes_inactive(self, db_session: Session):
        repo = BudgetRepository(db_session)
        active = repo.create(category="travel", amount=Decimal("2000"))
        inactive = repo.create(category="other", amount=Decimal("1000"))
        repo.update(inactive, is_active=False)
        active_categories = [b.category for b in repo.get_active()]
        assert "travel" in active_categories
        assert "other" not in active_categories
        assert active.is_active is True


class TestBudgetStatus:
    """Test suite for AnalyticsEngine.get_budget_status."""

    def _seed(self, session, spend):
        account = AccountRepository(session).create(
            bank_name="HDFC", account_identifier="1234", account_type="savings"
        )
        tx_repo = TransactionRepository(session)
        tx_repo.create(
            transaction_date=datetime.now(),
            amount=Decimal(spend),
            merchant="zomato",
            category="food_dining",
            account_id=account.id,
            transaction_type="debit",
        )
        BudgetRepository(session).create(
            category="food_dining", amount=Decimal("5000"), period="monthly"
        )
        session.commit()

    def test_under_budget(self, db_session: Session):
        self._seed(db_session, "1200")
        status = AnalyticsEngine().get_budget_status()
        food = next(s for s in status if s["category"] == "food_dining")
        assert food["spent"] == Decimal("1200")
        assert food["remaining"] == Decimal("3800")
        assert food["over_budget"] is False

    def test_over_budget(self, db_session: Session):
        self._seed(db_session, "6000")
        status = AnalyticsEngine().get_budget_status()
        food = next(s for s in status if s["category"] == "food_dining")
        assert food["over_budget"] is True
        assert food["percent_used"] == 120.0
