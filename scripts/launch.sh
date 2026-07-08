#!/usr/bin/env bash
#
# Launch the Expense Intelligence platform locally: the background agent
# (scheduler + FastAPI) and the Streamlit UI. Intended to be invoked by the
# launchd agent (see deploy/com.expenseintelligence.agent.plist) or run by hand.
#
set -euo pipefail

# Resolve the repo root regardless of where this script is called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Activate the virtualenv if present.
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Load environment variables from .env if present (never commit real secrets).
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"

cleanup() {
  echo "Shutting down..."
  # Kill child processes (agent + streamlit) on exit.
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting background agent (scheduler + FastAPI)..."
python -m scripts.run_agent &

echo "Starting Streamlit UI on port ${STREAMLIT_PORT}..."
streamlit run dashboard/app.py --server.port "${STREAMLIT_PORT}" &

# Wait for either process to exit.
wait -n
