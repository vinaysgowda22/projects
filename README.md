# Expense Intelligence

A local-first **Personal Finance Intelligence Platform**. It ingests bank
transaction emails from Gmail, parses them into structured transactions,
deduplicates and categorizes them, and surfaces analytics, budgets, and natural
language insights through a FastAPI backend and a Streamlit dashboard.

Everything runs on your machine. AI is optional — a `local_only` mode disables
all LLM calls and relies solely on the structured parsers and cached mappings.

## Features

- **Email ingestion** — Gmail `historyId`-based incremental sync (`keyring` for
  OAuth tokens, never plaintext files).
- **Per-bank parsers** — HDFC, ICICI, Axis, SBI, Amex, Kotak, with an optional
  AI fallback parser. Auto-selected via a parser registry.
- **Duplicate detection** — `gmail_id` → `reference_number` →
  `merchant + amount` within a time window (fuzzy matches are flagged, never
  auto-merged).
- **Categorization** — layered classifier (learned corrections → exact → fuzzy →
  pattern → optional AI) with persistent user-correction learning.
- **Analytics** — spend by category/merchant, income vs. expense, monthly/daily
  trends, and interval-regularity-based subscription detection.
- **Budgets** — per-category budgets with budget-vs-actual tracking.
- **Natural language queries** — LLM **function-calling** (never raw SQL).
- **Encrypted backup/export** — bundle and encrypt your data so a year of
  history isn't one disk failure away from gone.

## Requirements

- Python 3.12
- macOS (for the `launchd` agent and Keychain-backed OAuth token storage)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in values
python -m backend.config   # validates configuration, fails loudly if misconfigured
```

Initialize / migrate the database:

```bash
alembic upgrade head
```

## Running

Run the API and UI together (also used by the `launchd` agent):

```bash
./scripts/launch.sh
```

Or individually:

```bash
python -m scripts.run_agent                       # scheduler + FastAPI (:8000)
streamlit run dashboard/app.py                     # dashboard (:8501)
```

API docs are served at `http://127.0.0.1:8000/docs`.

## Deployment (macOS launchd agent)

Ship as a `launchd`-managed background agent (scheduler + FastAPI) with Streamlit
as the local UI. See `deploy/com.expenseintelligence.agent.plist` for the
per-user agent definition and installation steps. The agent runs as your user
(not root); secrets are loaded from `.env` / Keychain, never from the plist.

## Backup & restore

```python
from backend.services import get_backup_service

svc = get_backup_service()
svc.export("backups/expenses.backup")     # encrypted archive
svc.import_backup("backups/expenses.backup")
```

The encryption key is read from `BACKUP_ENCRYPTION_KEY` or the OS keyring
(generated on first use). See `docs/ARCHITECTURE.md` for details.

## Testing & quality gate

```bash
pytest              # test suite
ruff check .        # lint
black --check .     # formatting
isort --check .     # import ordering
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — locked architecture decisions,
  the AI data-flow, NL query functions, and the subscription algorithm.
- [`docs/BLOCKERS.md`](docs/BLOCKERS.md) — known blockers and open issues.
- [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md) — module-by-module build history.
