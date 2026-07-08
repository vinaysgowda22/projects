"""Transaction model for financial transactions."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.account import Account
    from backend.models.tag import TransactionTag


class Transaction(Base, TimestampMixin):
    """Represents a financial transaction."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Core transaction data
    transaction_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    merchant: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # Bank/provided identifiers
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reference_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    gmail_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    # Transaction type and status
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "debit", "credit", "transfer"
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="posted"
    )  # "pending", "posted"

    # Duplicate detection
    is_duplicate: Mapped[bool] = mapped_column(default=False, nullable=False)
    possible_duplicate: Mapped[bool] = mapped_column(default=False, nullable=False)
    parent_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Additional metadata
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_email_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship("Account", backref="transactions")
    parent_transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", remote_side=[id], backref="split_transactions"
    )
    tags: Mapped[list["TransactionTag"]] = relationship(
        "TransactionTag", back_populates="transaction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, date={self.transaction_date}, "
            f"amount={self.amount}, merchant={self.merchant})>"
        )
