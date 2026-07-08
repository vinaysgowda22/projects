"""Encrypted local backup/export and import of financial data (spec §5.10).

A year of financial history should not be one disk failure away from gone. This
service bundles the SQLite database (and the learned merchant-mapping file, if
present) into a single tar archive and encrypts it with a symmetric key using
``cryptography``'s Fernet (AES-128-CBC + HMAC).

Key management follows the same principle as OAuth tokens (§5.5): the encryption
key is never hardcoded. It is read from the ``BACKUP_ENCRYPTION_KEY`` environment
variable if set, otherwise from the OS keyring (generated and stored on first
use). A key may also be injected explicitly (useful for tests).
"""

import io
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import keyring
from cryptography.fernet import Fernet
from loguru import logger

from backend.config import get_config

KEYRING_SERVICE = "expense_intelligence_backup"
KEYRING_USERNAME = "backup_encryption_key"
ENV_KEY_NAME = "BACKUP_ENCRYPTION_KEY"

# Archive member names.
_DB_MEMBER = "expenses.db"
_MAPPING_MEMBER = "merchant_mapping.json"


def _load_or_create_key() -> bytes:
    """Return the Fernet key from env or keyring, generating one if needed."""
    env_key = os.environ.get(ENV_KEY_NAME)
    if env_key:
        return env_key.encode()

    stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if stored:
        return stored.encode()

    key = Fernet.generate_key()
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, key.decode())
    logger.info("Generated new backup encryption key and stored it in the keyring")
    return key


class BackupService:
    """Create and restore encrypted backups of the platform's data."""

    def __init__(
        self,
        key: Optional[bytes] = None,
        db_path: Optional[Path] = None,
        mapping_path: Optional[Path] = None,
    ):
        """Initialize the backup service.

        Args:
            key: Fernet key. If None, resolved from env/keyring.
            db_path: SQLite DB path. Defaults to the configured database path.
            mapping_path: Learned merchant-mapping file to include, if present.
        """
        self._key = key or _load_or_create_key()
        self._fernet = Fernet(self._key)
        self.db_path = Path(db_path) if db_path else Path(get_config().database.path)
        self.mapping_path = (
            Path(mapping_path) if mapping_path else Path("config/merchant_mapping.json")
        )

    def export(self, output_path: Path) -> Path:
        """Create an encrypted backup archive.

        Args:
            output_path: Destination file (e.g. ``backups/expenses.backup``).

        Returns:
            The path written.

        Raises:
            FileNotFoundError: If the database file does not exist.
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        # Build the tar archive in memory.
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            tar.add(self.db_path, arcname=_DB_MEMBER)
            if self.mapping_path.exists():
                tar.add(self.mapping_path, arcname=_MAPPING_MEMBER)

        token = self._fernet.encrypt(buffer.getvalue())

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(token)
        logger.info(f"Encrypted backup written to {output_path}")
        return output_path

    def import_backup(
        self, input_path: Path, restore_db_path: Optional[Path] = None
    ) -> Path:
        """Restore the database from an encrypted backup archive.

        Args:
            input_path: Encrypted backup file produced by :meth:`export`.
            restore_db_path: Where to write the restored DB. Defaults to the
                configured database path.

        Returns:
            The path the database was restored to.

        Raises:
            FileNotFoundError: If the backup file does not exist.
            ValueError: If the backup cannot be decrypted (wrong key/corrupt).
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Backup not found at {input_path}")

        from cryptography.fernet import InvalidToken

        try:
            plaintext = self._fernet.decrypt(input_path.read_bytes())
        except InvalidToken as e:
            raise ValueError(
                "Failed to decrypt backup (wrong key or corrupted file)"
            ) from e

        restore_db_path = Path(restore_db_path) if restore_db_path else self.db_path
        restore_db_path.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(plaintext), mode="r:gz") as tar:
            with tempfile.TemporaryDirectory() as tmpdir:
                member = tar.getmember(_DB_MEMBER)
                tar.extract(member, path=tmpdir, filter="data")
                extracted = Path(tmpdir) / _DB_MEMBER
                restore_db_path.write_bytes(extracted.read_bytes())

                # Restore the learned mapping file when present.
                if _MAPPING_MEMBER in tar.getnames():
                    tar.extract(
                        tar.getmember(_MAPPING_MEMBER), path=tmpdir, filter="data"
                    )
                    self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
                    self.mapping_path.write_bytes(
                        (Path(tmpdir) / _MAPPING_MEMBER).read_bytes()
                    )

        logger.info(f"Database restored to {restore_db_path}")
        return restore_db_path


# Global service instance
_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get the global backup service instance (singleton pattern)."""
    global _service
    if _service is None:
        _service = BackupService()
    return _service


def reset_backup_service() -> None:
    """Reset the global backup service (useful for testing)."""
    global _service
    _service = None
