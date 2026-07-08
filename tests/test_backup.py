"""Tests for the encrypted backup/export service (§5.10)."""

import pytest
from cryptography.fernet import Fernet

from backend.services.backup_service import BackupService


def _service(tmp_path, key=None):
    db = tmp_path / "db" / "expenses.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"SQLite format 3\x00-original-data")
    mapping = tmp_path / "config" / "merchant_mapping.json"
    mapping.parent.mkdir(parents=True, exist_ok=True)
    mapping.write_text('{"acme corp": "shopping"}')
    svc = BackupService(
        key=key or Fernet.generate_key(), db_path=db, mapping_path=mapping
    )
    return svc, db, mapping


def test_export_creates_encrypted_file(tmp_path):
    svc, db, _ = _service(tmp_path)
    out = svc.export(tmp_path / "backups" / "data.backup")
    assert out.exists()
    # The archive must be encrypted, not the raw (recognizable) DB bytes.
    assert b"-original-data" not in out.read_bytes()


def test_export_import_roundtrip_restores_db(tmp_path):
    svc, db, mapping = _service(tmp_path)
    backup = svc.export(tmp_path / "backups" / "data.backup")

    # Simulate data loss.
    db.write_bytes(b"corrupted")
    mapping.write_text("{}")

    svc.import_backup(backup)
    assert db.read_bytes() == b"SQLite format 3\x00-original-data"
    assert mapping.read_text() == '{"acme corp": "shopping"}'


def test_import_with_wrong_key_fails(tmp_path):
    svc, _, _ = _service(tmp_path)
    backup = svc.export(tmp_path / "backups" / "data.backup")

    wrong = BackupService(
        key=Fernet.generate_key(),
        db_path=tmp_path / "db" / "expenses.db",
        mapping_path=tmp_path / "config" / "merchant_mapping.json",
    )
    with pytest.raises(ValueError, match="decrypt"):
        wrong.import_backup(backup)


def test_export_missing_db_raises(tmp_path):
    svc = BackupService(
        key=Fernet.generate_key(),
        db_path=tmp_path / "nope.db",
        mapping_path=tmp_path / "config" / "merchant_mapping.json",
    )
    with pytest.raises(FileNotFoundError):
        svc.export(tmp_path / "out.backup")
