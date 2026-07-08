"""Repository for FailedEmail model."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.failed_email import FailedEmail
from backend.repositories.base_repository import BaseRepository


class FailedEmailRepository(BaseRepository[FailedEmail]):
    """Repository for FailedEmail operations."""

    def __init__(self, session: Session):
        """Initialize FailedEmailRepository."""
        super().__init__(FailedEmail, session)

    def get_by_gmail_id(self, gmail_id: str) -> Optional[FailedEmail]:
        """Get failed email by Gmail ID."""
        return (
            self.session.query(FailedEmail)
            .filter(FailedEmail.gmail_id == gmail_id)
            .first()
        )

    def get_by_sender(self, sender: str, limit: int = 100) -> List[FailedEmail]:
        """Get failed emails by sender."""
        return (
            self.session.query(FailedEmail)
            .filter(FailedEmail.sender == sender)
            .limit(limit)
            .all()
        )

    def get_retry_candidates(self, max_retry_count: int = 3) -> List[FailedEmail]:
        """Get failed emails that can be retried (below max retry count)."""
        return (
            self.session.query(FailedEmail)
            .filter(FailedEmail.retry_count < max_retry_count)
            .order_by(FailedEmail.processed_at.desc())
            .all()
        )

    def increment_retry(self, failed_email: FailedEmail) -> FailedEmail:
        """Increment retry count and update last retry timestamp."""
        return self.update(
            failed_email,
            retry_count=failed_email.retry_count + 1,
            last_retry_at=datetime.now(),
        )
