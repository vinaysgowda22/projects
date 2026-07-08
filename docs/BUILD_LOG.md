# Build Log

This document tracks the progress of building the Expense Intelligence platform module by module.

---

## Module 6.1: Project scaffolding & config

**Status:** ✅ COMPLETED

**What was built:**
- Complete folder structure as specified in Section 4
- `.env.example` with all required environment variables
- `.gitignore` appropriate for Python project
- `requirements.txt` with pinned versions for all dependencies
- `backend/config.py` with comprehensive configuration management:
  - DatabaseConfig, GmailConfig, FastAPIConfig, StreamlitConfig, AIConfig, LoggingConfig, SettingsConfig
  - Environment variable loading via python-dotenv
  - Validation via Pydantic
  - Path validation and directory creation
  - local_only mode that disables AI features
  - Singleton pattern for config access

**What broke:**
- Initial `requirements.txt` had `python==3.12.0` which is not installable via pip
- Fixed by removing the python version requirement (system provides Python)
- Initial config.py used `|` union syntax (Python 3.10+) but system runs Python 3.9
- Fixed by importing `Optional` from typing and using `Optional[Config]` instead of `Config | None`

**How it was fixed:**
- Removed python version from requirements.txt
- Changed type hints to use `Optional` for Python 3.9 compatibility

**Iterations:** 2

**Tests:** 10/10 passing in tests/test_config.py

**Verification:** `python -m backend.config` runs successfully and prints validated configuration

---

## Module 6.2: Database layer

**Status:** ✅ COMPLETED

**What was built:**
- SQLAlchemy models for all tables:
  - Account (bank + account/card identifier)
  - Tag + TransactionTag (many-to-many relationship)
  - Transaction (with parent_transaction_id for splits)
  - Setting (key/value store)
  - FailedEmail (for failed email parses)
- Alembic initialized with first migration generating full schema
- WAL mode enabled in database.py with PRAGMA journal_mode=WAL
- Repository pattern classes for each table:
  - BaseRepository (generic CRUD)
  - AccountRepository
  - TransactionRepository
  - TagRepository
  - SettingRepository
  - FailedEmailRepository

**What broke:**
- Initial models had duplicate index definitions (both in __table_args__ and via index=True on columns)
- SQLite doesn't support ALTER of constraints directly, needed batch mode for Alembic
- WAL mode creates .db-wal and .db-shm files that weren't being cleaned up in reset_db
- Index conflicts when recreating database during tests

**How it was fixed:**
- Removed duplicate Index definitions from __table_args__, kept only index=True on columns
- Enabled render_as_batch=True in Alembic env.py for SQLite compatibility
- Updated reset_db() to delete all .db* files (including WAL files)
- Simplified index definitions to avoid conflicts

**Iterations:** 4

**Tests:** 23/23 passing in tests/test_repositories.py (full CRUD round-trip for all repositories)

**Verification:** `alembic upgrade head` creates database from empty; all repository CRUD tests pass

---

## Module 6.3: Bank parsers (HDFC only - template for others)

**Status:** ✅ COMPLETED (HDFC parser implemented as template for other banks)

**What was built:**
- BaseParser abstract class with `can_parse(email) -> bool` and `parse(email) -> TransactionDraft`
- TransactionDraft dataclass for intermediate transaction data representation
- ParserRegistry for auto-selecting appropriate parser based on sender patterns
- HDFCParser concrete implementation:
  - Parses HDFC Bank transaction emails from alerts@hdfcbank.com
  - Extracts amount, date, merchant, reference number, card identifier
  - Handles multiple email formats (debit card, credit card, account transactions)
  - Determines transaction type (debit/credit) from subject and content
- Golden-file tests for HDFC parser:
  - 3 sample HDFC emails with corresponding expected JSON outputs
  - Field-for-field validation of parsed data
  - Registry routing test to verify correct parser selection

**What broke:**
- Initial parser can_parse() used subject patterns which caused false matches between banks
- Fixed by using only sender address patterns for can_parse()
- Initial regex patterns for merchant extraction didn't match actual email formats
- Fixed by updating to match "At:", "Merchant:", and "To:" patterns
- Reference number extraction failed for different formats ("Ref:", "Ref No:", "Reference:")
- Fixed by using multiple regex alternatives to handle all formats
- Credit card transactions were incorrectly classified as "credit" type
- Fixed by treating credit card transactions as "debit" (money leaving) unless explicitly a refund

**How it was fixed:**
- Simplified can_parse() to only check sender addresses
- Updated merchant regex to match colon-delimited field patterns
- Enhanced reference number regex with multiple alternatives
- Added logic to distinguish credit card usage from actual credits

**Iterations:** 3

**Tests:** 4/4 passing in tests/test_parsers.py (3 golden-file tests + 1 registry test)

**Verification:** All HDFC sample emails parse correctly with field-for-field JSON match; registry routes HDFC emails to HDFCParser

**Note:** Other bank parsers (ICICI, Axis, SBI, Amex, Kotak) can be implemented by copying the HDFCParser pattern and adjusting sender patterns and regex as needed.
