"""Persistent store for learned merchant → category mappings.

This backs the user-correction learning and AI-result caching described in
spec §6.5: once a merchant's category is corrected by the user or resolved by
the AI layer, it is persisted here so future transactions from that merchant
are categorized deterministically without re-asking (or re-paying the AI cost).

The store is a small JSON file keyed by the *normalized* merchant string.
"""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

DEFAULT_MAPPING_PATH = Path("config/merchant_mapping.json")


class MerchantMappingStore:
    """JSON-backed key/value store of normalized merchant -> category."""

    def __init__(self, path: Optional[Path] = None):
        """Initialize the store.

        Args:
            path: Path to the JSON mapping file. Defaults to
                ``config/merchant_mapping.json``.
        """
        self.path = Path(path) if path else DEFAULT_MAPPING_PATH
        self._mappings: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        """Load mappings from disk, returning an empty dict if absent."""
        if not self.path.exists():
            return {}
        try:
            with open(self.path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(f"Malformed mapping file {self.path}; ignoring")
                return {}
            return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load mapping file {self.path}: {e}")
            return {}

    def _persist(self) -> None:
        """Write mappings to disk, creating parent directories as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._mappings, f, indent=2, sort_keys=True)

    def get(self, normalized_merchant: str) -> Optional[str]:
        """Return the learned category for a normalized merchant, if any."""
        return self._mappings.get(normalized_merchant)

    def set(self, normalized_merchant: str, category: str) -> None:
        """Persist a learned mapping for a normalized merchant."""
        if not normalized_merchant or not category:
            return
        self._mappings[normalized_merchant] = category
        self._persist()
        logger.info(
            f"Learned merchant mapping: '{normalized_merchant}' -> '{category}'"
        )

    def all(self) -> dict[str, str]:
        """Return a copy of all learned mappings."""
        return dict(self._mappings)


# Global store instance
_store: Optional[MerchantMappingStore] = None


def get_merchant_mapping_store() -> MerchantMappingStore:
    """Get the global merchant mapping store (singleton pattern)."""
    global _store
    if _store is None:
        _store = MerchantMappingStore()
    return _store


def reset_merchant_mapping_store() -> None:
    """Reset the global merchant mapping store (useful for testing)."""
    global _store
    _store = None
