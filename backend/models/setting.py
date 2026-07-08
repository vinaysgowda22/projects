"""Setting model for application configuration stored in database."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """Key-value store for application settings."""

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("key", name="uq_setting_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)

    def __repr__(self) -> str:
        return f"<Setting(key={self.key}, value={self.value})>"
