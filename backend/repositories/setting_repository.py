"""Repository for Setting model."""

from typing import Optional

from sqlalchemy.orm import Session

from backend.models.setting import Setting
from backend.repositories.base_repository import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    """Repository for Setting operations."""
    
    def __init__(self, session: Session):
        """Initialize SettingRepository."""
        super().__init__(Setting, session)
    
    def get_by_key(self, key: str) -> Optional[Setting]:
        """Get setting by key."""
        return self.session.query(Setting).filter(Setting.key == key).first()
    
    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get setting value by key, with optional default."""
        setting = self.get_by_key(key)
        return setting.value if setting else default
    
    def set_value(self, key: str, value: str, description: str) -> Setting:
        """Set a setting value (create or update)."""
        setting = self.get_by_key(key)
        if setting:
            self.update(setting, value=value, description=description)
        else:
            setting = self.create(key=key, value=value, description=description)
        return setting
