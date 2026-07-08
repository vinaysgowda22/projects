"""FailedEmail model for emails that could not be parsed."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class FailedEmail(Base, TimestampMixin):
    """Represents an email that failed to parse (both structured and AI parsing)."""
    
    __tablename__ = "failed_emails"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gmail_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sender: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    received_at: Mapped[datetime] = mapped_column(nullable=False)
    
    # Parsing failure details
    failure_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    parser_attempted: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "hdfc", "ai_fallback"
    
    # For reprocessing attempts
    processed_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Raw email content for manual review
    raw_body_snippet: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    
    def __repr__(self) -> str:
        return f"<FailedEmail(id={self.id}, gmail_id={self.gmail_id}, reason={self.failure_reason})>"
