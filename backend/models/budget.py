"""Budget model for per-category spending limits."""

from decimal import Decimal

from sqlalchemy import Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class Budget(Base, TimestampMixin):
    """A spending limit for a category over a recurring period."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("category", "period", name="uq_budget_category_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )  # "monthly", "weekly", "yearly"
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Budget(id={self.id}, category={self.category}, "
            f"amount={self.amount}, period={self.period})>"
        )
