"""Tag and TransactionTag models for transaction tagging."""

from typing import Optional

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """Represents a tag that can be applied to transactions."""
    
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Relationships
    transaction_tags: Mapped[list["TransactionTag"]] = relationship(
        "TransactionTag", back_populates="tag", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"


class TransactionTag(Base, TimestampMixin):
    """Many-to-many relationship between transactions and tags."""
    
    __tablename__ = "transaction_tags"
    __table_args__ = (UniqueConstraint("transaction_id", "tag_id", name="uq_transaction_tag"),)
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="tags")
    tag: Mapped[Tag] = relationship("Tag", back_populates="transaction_tags")
    
    def __repr__(self) -> str:
        return f"<TransactionTag(transaction_id={self.transaction_id}, tag_id={self.tag_id})>"
