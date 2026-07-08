"""FastAPI main application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from backend.api.routes import (
    accounts,
    budgets,
    failed_emails,
    settings,
    tags,
    transactions,
)
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up FastAPI application")
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title="Expense Intelligence API",
    description="Personal Finance Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(
    transactions.router, prefix="/api/transactions", tags=["transactions"]
)
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(
    failed_emails.router, prefix="/api/failed-emails", tags=["failed-emails"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Expense Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
