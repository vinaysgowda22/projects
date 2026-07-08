"""Repository for Tag and TransactionTag models."""

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.tag import Tag, TransactionTag
from backend.repositories.base_repository import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for Tag operations."""

    def __init__(self, session: Session):
        """Initialize TagRepository."""
        super().__init__(Tag, session)

    def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name."""
        return self.session.query(Tag).filter(Tag.name == name).first()

    def get_or_create(self, name: str, **kwargs) -> Tag:
        """Get existing tag or create a new one."""
        tag = self.get_by_name(name)
        if tag is None:
            tag = self.create(name=name, **kwargs)
        return tag

    def add_tag_to_transaction(
        self, transaction_id: int, tag_id: int
    ) -> TransactionTag:
        """Add a tag to a transaction."""
        # Check if already exists
        existing = (
            self.session.query(TransactionTag)
            .filter(
                TransactionTag.transaction_id == transaction_id,
                TransactionTag.tag_id == tag_id,
            )
            .first()
        )
        if existing:
            return existing

        transaction_tag = TransactionTag(transaction_id=transaction_id, tag_id=tag_id)
        self.session.add(transaction_tag)
        self.session.flush()
        return transaction_tag

    def remove_tag_from_transaction(self, transaction_id: int, tag_id: int) -> None:
        """Remove a tag from a transaction."""
        transaction_tag = (
            self.session.query(TransactionTag)
            .filter(
                TransactionTag.transaction_id == transaction_id,
                TransactionTag.tag_id == tag_id,
            )
            .first()
        )
        if transaction_tag:
            self.session.delete(transaction_tag)
            self.session.flush()

    def get_tags_for_transaction(self, transaction_id: int) -> List[Tag]:
        """Get all tags for a transaction."""
        return (
            self.session.query(Tag)
            .join(TransactionTag)
            .filter(TransactionTag.transaction_id == transaction_id)
            .all()
        )
