# Architecture

This document records the locked-in architecture decisions and, per spec §5.3 /
§5.4 / §5.8, documents exactly what is sent to the AI provider, the natural
language query functions, and the subscription-detection algorithm.

## Component overview

```
Gmail ──(historyId incremental sync)──▶ gmail_service
   │
   ▼
TransactionPipeline
   ├─ ParserRegistry ── per-bank regex parsers ── AI fallback parser (optional)
   ├─ DuplicateDetector
   └─ CategoryClassifier
   │
   ▼
SQLite (WAL) ◀── repository layer ──▶ AnalyticsEngine / InsightsEngine
   │                                        │
   ▼                                        ▼
FastAPI  ◀────────────────────────────  Streamlit dashboard
```

All three runtime surfaces (FastAPI, Streamlit, APScheduler) touch the same
SQLite file. WAL mode is enabled at connection setup and **all writes go through
the repository layer** — no ad hoc connections (§5.6).

## Data model (§5.1)

`Accounts`, `Transactions` (with self-FK `parent_transaction_id` for splits),
`Tags` + `TransactionTags` (many-to-many), `Settings` (key/value), `Budgets`
(per-category limits), and `FailedEmails` (emails where both structured and AI
parsing failed — persisted, never silently dropped).

## AI safety boundaries (§5.3)

AI is optional and gated by `AI_ENABLED` / `local_only`. When disabled, only the
structured parsers and cached mappings run.

**What is sent to the AI provider:**

| Path | Input sent to the LLM | Notes |
|------|-----------------------|-------|
| AI fallback parser (`parsers/ai_parser.py`) | The email body **stripped to plain text** via BeautifulSoup (HTML removed). Subject/sender included as context. | Used only when no structured parser matches. |
| AI category classifier (`categorization/category_classifier.py`, Layer 3b) | Only the **normalized merchant string** (e.g. `"amazon"`), plus the fixed list of allowed categories. | No amounts, dates, or account data. |
| NL query engine (`insights/insights_engine.py`) | The user's question plus the **function schemas** (names/descriptions). The DB is queried locally; only aggregated results are sent back to the LLM to phrase an answer. | Never sends raw rows or raw SQL. |

**Treated as untrusted:** every LLM output is validated against a strict schema
(types + regex for amounts/dates/reference numbers) before it can touch the
database. LLM output can only ever produce a *candidate transaction record* — it
never triggers actions, and instructions embedded in email bodies are never
executed.

**Caching:** once a merchant is categorized by the AI it is written to the
learned merchant-mapping store (`config/merchant_mapping.json`) and never
re-queried. User corrections are persisted the same way.

## Natural language query engine (§5.4)

Implemented as **function-calling**, not text-to-SQL. The LLM selects one of a
fixed set of functions and fills its arguments; the platform executes the
function locally against the repository layer. The LLM never generates or
executes SQL.

Available functions (`InsightsEngine`):

- `get_spending_by_category(start_date, end_date)`
- `get_spending_by_merchant(start_date, end_date, limit)`
- `get_income_vs_expense(start_date, end_date)`
- `get_subscriptions()`
- `get_monthly_spending(months)`

## Subscription / recurring detection (§5.8)

Implemented in `AnalyticsEngine.get_subscriptions` and its helpers. The
algorithm is interval-regularity based — it is **not** enough for the amounts to
be similar; the *time between* charges must be regular.

1. **Group by merchant.** Consider each merchant's debit transactions.
2. **Cluster by amount** (`_cluster_by_amount`). Within a merchant, group charges
   whose amounts are within **±10%** (`SUBSCRIPTION_AMOUNT_TOLERANCE`) of each
   other — this tolerates small price changes (taxes, fees, plan tweaks).
3. **Check interval regularity** (`_detect_cadence`). Sort each cluster by date
   and compute the day-gaps between consecutive charges. A cluster is a
   subscription only if **every** gap falls inside a single cadence band:

   | Cadence   | Gap range (days) |
   |-----------|------------------|
   | weekly    | 4–10             |
   | monthly   | 25–34 (≈28–31 ±3)|
   | quarterly | 86–96            |
   | yearly    | 360–370          |

   The bands bake in the spec's ±3-day tolerance.
4. **Occurrence threshold.** Strict mode requires **3+** charges (≥2 regular
   intervals). For known-subscription merchants (`SUBSCRIPTION_PATTERNS`, e.g.
   Netflix/Spotify) a lenient path accepts a single regular interval (2 charges).

The result includes the detected `frequency` (cadence label), `occurrences`,
and the average amount. Two similar one-off purchases a few days apart are
therefore **not** flagged as a subscription.

## Categorization layers (§6.5)

`CategoryClassifier.classify` runs, in order:

- **Layer 0** — learned mappings (user corrections + cached AI results).
- **Layer 1** — exact match on normalized merchant.
- **Layer 2** — fuzzy match (`rapidfuzz`).
- **Layer 3a** — pattern match.
- **Layer 3b** — optional AI classification, constrained to known categories and
  cached back to Layer 0.

Merchant normalization (§5.7) strips `POS`, `UPI/`, trailing reference numbers,
and normalizes case/whitespace **before** any layer runs.

## Deployment (§5.9)

A `launchd` LaunchAgent (`deploy/com.expenseintelligence.agent.plist`) runs
`scripts/launch.sh`, which starts the background agent (scheduler + FastAPI via
`scripts/run_agent.py`) and the Streamlit UI. It runs as the logged-in user, not
root.

## Backup/export (§5.10)

`backend/services/backup_service.py` bundles the SQLite DB and the learned
merchant-mapping file into a gzip tar archive and encrypts it with Fernet
(AES-128-CBC + HMAC). The key comes from `BACKUP_ENCRYPTION_KEY` or the OS
keyring (generated on first use) — never hardcoded. Import decrypts and restores
the database (and mapping) to the configured paths; a wrong key fails loudly.
