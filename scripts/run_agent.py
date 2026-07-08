"""Background agent entrypoint: runs the email-sync scheduler + FastAPI.

This is what the ``launchd`` agent (spec §5.9) launches. It starts the
APScheduler-based email sync in-process and then serves the FastAPI app with
uvicorn. The Streamlit UI is launched separately (see ``scripts/launch.sh``).
"""

import uvicorn
from loguru import logger

from backend.config import get_config
from backend.pipeline.scheduler import get_scheduler


def main() -> None:
    """Start the scheduler and run the FastAPI server (blocking)."""
    config = get_config()

    scheduler = get_scheduler()
    try:
        scheduler.start()
    except Exception as e:  # pragma: no cover - depends on Gmail creds at runtime
        logger.warning(f"Scheduler failed to start (continuing with API only): {e}")

    try:
        uvicorn.run(
            "backend.api.main:app",
            host=config.fastapi.host,
            port=config.fastapi.port,
            reload=False,
        )
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
